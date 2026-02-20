import os
import re
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from models.schemas import RetrievalChunk


class RAGEngine:
    """
    Simple RAG implementation for underwriting guideline retrieval.
    Uses sentence transformers for embeddings and ChromaDB for vector storage.
    """
    
    def __init__(self, data_dir: str = "data/guidelines"):
        self.data_dir = Path(data_dir)
        self.chroma_client = chromadb.PersistentClient(path="./storage/chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="underwriting_guidelines",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunk_size = 500  # characters
        self.chunk_overlap = 50  # characters
        
    def ingest_documents(self, force_reingest: bool = False):
        """
        Ingest all markdown documents from the guidelines directory.
        """
        if force_reingest:
            self.collection.delete()
        
        # Check if documents already exist
        if self.collection.count() > 0 and not force_reingest:
            print(f"Collection already has {self.collection.count()} documents")
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for doc_file in self.data_dir.glob("*.md"):
            doc_content = doc_file.read_text(encoding='utf-8')
            doc_id = doc_file.stem
            doc_version = "v1.0"  # Simple versioning
            
            # Split into sections based on headers
            sections = self._split_into_sections(doc_content)
            
            for section_title, section_content in sections:
                # Split section into chunks
                chunks = self._chunk_text(section_content)
                
                for i, chunk in enumerate(chunks):
                    # Add unique identifier using UUID to avoid duplicates
                    unique_id = str(uuid.uuid4())[:8]
                    chunk_id = f"{doc_id}_{section_title}_{i}_{unique_id}"
                    documents.append(chunk)
                    
                    metadatas.append({
                        "doc_id": doc_id,
                        "doc_version": doc_version,
                        "section": section_title,
                        "chunk_id": chunk_id,
                        "source_file": str(doc_file)
                    })
                    
                    ids.append(chunk_id)
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(documents)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings.tolist()
        )
        
        print(f"Ingested {len(documents)} chunks from {len(set(m['doc_id'] for m in metadatas))} documents")
    
    def _split_into_sections(self, content: str) -> List[tuple]:
        """
        Split document into sections based on markdown headers.
        """
        sections = []
        lines = content.split('\n')
        current_section = "Overview"
        current_content = []
        
        for line in lines:
            if line.startswith('#'):
                # Save previous section
                if current_content:
                    sections.append((current_section, '\n'.join(current_content)))
                
                # Start new section
                current_section = line.strip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add last section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))
        
        return sections
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at word boundary
            if end < len(text):
                while end > start and text[end] != ' ':
                    end -= 1
                if end == start:
                    end = start + self.chunk_size
            
            chunks.append(text[start:end].strip())
            
            # Move start with overlap
            start = max(start + 1, end - self.chunk_overlap)
        
        return [chunk for chunk in chunks if chunk]
    
    def retrieve(self, query: str, n_results: int = 5) -> List[RetrievalChunk]:
        """
        Retrieve relevant chunks for a given query.
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Search collection
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to RetrievalChunk objects
        chunks = []
        for i in range(len(results['documents'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            # Convert distance to similarity score (cosine distance to similarity)
            similarity_score = 1 - distance
            
            chunk = RetrievalChunk(
                doc_id=metadata['doc_id'],
                doc_version=metadata['doc_version'],
                section=metadata['section'],
                chunk_id=metadata['chunk_id'],
                text=results['documents'][0][i],
                metadata=metadata,
                relevance_score=similarity_score
            )
            chunks.append(chunk)
        
        return chunks
    
    def get_document_summary(self) -> Dict[str, Any]:
        """
        Get summary of ingested documents.
        """
        docs = self.collection.get(include=['metadatas'])
        
        doc_stats = {}
        for metadata in docs['metadatas']:
            doc_id = metadata['doc_id']
            if doc_id not in doc_stats:
                doc_stats[doc_id] = {
                    'sections': set(),
                    'chunk_count': 0
                }
            
            doc_stats[doc_id]['sections'].add(metadata['section'])
            doc_stats[doc_id]['chunk_count'] += 1
        
        summary = {}
        for doc_id, stats in doc_stats.items():
            summary[doc_id] = {
                'sections': list(stats['sections']),
                'chunk_count': stats['chunk_count']
            }
        
        return summary
