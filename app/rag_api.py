"""
RAG API Integration for Evidence-First Underwriting

Provides API endpoints for RAG-powered decision making
with evidence verification and citation tracking.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from app.rag_engine import get_rag_engine
from app.evidence_verifier import get_evidence_verifier
from app.decision_composer import get_decision_composer
from models.schemas import QuoteSubmission

router = APIRouter(prefix="/api/rag", tags=["rag"])
logger = logging.getLogger(__name__)


class RAGQuery(BaseModel):
    """RAG query request"""
    query: str
    n_results: int = 5
    filters: Optional[Dict[str, Any]] = None


class EvidenceVerificationRequest(BaseModel):
    """Evidence verification request"""
    chunks: List[Dict[str, Any]]
    query_type: str


class DecisionCompositionRequest(BaseModel):
    """Decision composition request"""
    chunks: List[Dict[str, Any]]
    query_type: str
    submission_data: Optional[Dict[str, Any]] = None


class RAGDecisionRequest(BaseModel):
    """Complete RAG decision request"""
    submission: QuoteSubmission
    query_type: str = "eligibility"


@router.post("/query")
async def query_rag(request: RAGQuery):
    """
    Query RAG engine for relevant evidence
    
    Args:
        request: RAG query with filters
        
    Returns:
        Retrieved evidence chunks with relevance scores
    """
    try:
        rag = get_rag_engine()
        
        # Retrieve evidence
        chunks = rag.retrieve(
            query=request.query,
            n_results=request.n_results,
            filters=request.filters
        )
        
        # Convert to response format
        response = {
            "query": request.query,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "doc_title": chunk.metadata.get("doc_title", "Unknown"),
                    "section": chunk.section,
                    "text": chunk.text,
                    "relevance_score": chunk.relevance_score,
                    "metadata": chunk.metadata
                }
                for chunk in chunks
            ],
            "total_chunks": len(chunks)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@router.post("/verify-evidence")
async def verify_evidence(request: EvidenceVerificationRequest):
    """
    Verify evidence quality and confidence
    
    Args:
        request: Evidence verification request
        
    Returns:
        Evidence quality assessment
    """
    try:
        verifier = get_evidence_verifier()
        
        # Convert chunks to RetrievalChunk objects
        from models.schemas import RetrievalChunk
        chunks = []
        for chunk_data in request.chunks:
            chunk = RetrievalChunk(
                doc_id=chunk_data["doc_id"],
                doc_version=chunk_data.get("doc_version", "v1.0"),
                section=chunk_data["section"],
                chunk_id=chunk_data["chunk_id"],
                text=chunk_data["text"],
                metadata=chunk_data.get("metadata", {}),
                relevance_score=chunk_data.get("relevance_score")
            )
            chunks.append(chunk)
        
        # Verify evidence
        assessment = verifier.verify_evidence(chunks, request.query_type)
        
        # Convert to response format
        response = {
            "quality": assessment.quality.value,
            "confidence_score": assessment.confidence_score,
            "rule_strength": assessment.rule_strength.value,
            "has_thresholds": assessment.has_thresholds,
            "has_conditions": assessment.has_conditions,
            "cross_reference_count": assessment.cross_reference_count,
            "recommendations": assessment.recommendations,
            "verification_details": assessment.verification_details
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Evidence verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Evidence verification failed: {str(e)}")


@router.post("/compose-decision")
async def compose_decision(request: DecisionCompositionRequest):
    """
    Compose evidence-based decision
    
    Args:
        request: Decision composition request
        
    Returns:
        Structured decision with evidence mapping
    """
    try:
        composer = get_decision_composer()
        
        # Convert chunks to RetrievalChunk objects
        from models.schemas import RetrievalChunk
        chunks = []
        for chunk_data in request.chunks:
            chunk = RetrievalChunk(
                doc_id=chunk_data["doc_id"],
                doc_version=chunk_data.get("doc_version", "v1.0"),
                section=chunk_data["section"],
                chunk_id=chunk_data["chunk_id"],
                text=chunk_data["text"],
                metadata=chunk_data.get("metadata", {}),
                relevance_score=chunk_data.get("relevance_score")
            )
            chunks.append(chunk)
        
        # Compose decision
        decision = composer.compose_decision(
            chunks=chunks,
            query_type=request.query_type,
            submission_data=request.submission_data
        )
        
        # Convert to response format
        response = {
            "decision_type": decision.decision_type.value,
            "primary_reason": decision.primary_reason,
            "confidence_score": decision.confidence_score,
            "evidence_map": {
                component: {
                    "chunk_ids": evidence.chunk_ids,
                    "excerpts": evidence.excerpts,
                    "relevance_scores": evidence.relevance_scores,
                    "rule_strengths": evidence.rule_strengths,
                    "confidence": evidence.confidence
                }
                for component, evidence in decision.evidence_map.items()
            },
            "required_questions": decision.required_questions,
            "referral_triggers": decision.referral_triggers,
            "conditions": decision.conditions,
            "endorsements": decision.endorsements,
            "citations": [
                {
                    "citation_id": citation["citation_id"],
                    "doc_title": citation["doc_title"],
                    "section": citation["section"],
                    "text_excerpt": citation["text_excerpt"],
                    "relevance_score": citation["relevance_score"],
                    "rule_strength": citation["rule_strength"],
                    "effective_date": citation["effective_date"]
                }
                for citation in decision.citations
            ]
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Decision composition error: {e}")
        raise HTTPException(status_code=500, detail=f"Decision composition failed: {str(e)}")


@router.post("/underwriting-decision")
async def generate_underwriting_decision(request: RAGDecisionRequest):
    """
    Generate complete underwriting decision using RAG
    
    Args:
        request: Underwriting decision request
        
    Returns:
        Complete decision with evidence and reasoning
    """
    try:
        # Initialize components
        rag = get_rag_engine()
        verifier = get_evidence_verifier()
        composer = get_decision_composer()
        
        # Build RAG query from submission
        query_parts = [
            f"property type {request.submission.property_type}",
            f"coverage amount {request.submission.coverage_amount}",
            f"construction year {request.submission.construction_year}",
            f"roof type {request.submission.roof_type}",
            f"square footage {request.submission.square_footage}",
            f"{request.query_type} requirements"
        ]
        query = " ".join(query_parts)
        
        # Retrieve evidence
        chunks = rag.retrieve(query, n_results=5)
        
        # Verify evidence
        assessment = verifier.verify_evidence(chunks, request.query_type)
        
        # Compose decision
        decision = composer.compose_decision(
            chunks=chunks,
            query_type=request.query_type,
            submission_data=request.submission.dict()
        )
        
        # Build complete response
        response = {
            "submission": request.submission.dict(),
            "query": query,
            "decision": {
                "type": decision.decision_type.value,
                "confidence": decision.confidence_score,
                "reason": decision.primary_reason
            },
            "evidence": {
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "doc_title": chunk.metadata.get("doc_title", "Unknown"),
                        "section": chunk.section,
                        "text": chunk.text,
                        "relevance_score": chunk.relevance_score,
                        "rule_strength": chunk.metadata.get("rule_strength", "informational")
                    }
                    for chunk in chunks
                ],
                "assessment": {
                    "quality": assessment.quality.value,
                    "confidence": assessment.confidence_score,
                    "rule_strength": assessment.rule_strength.value,
                    "has_thresholds": assessment.has_thresholds,
                    "cross_references": assessment.cross_reference_count
                }
            },
            "required_questions": decision.required_questions,
            "referral_triggers": decision.referral_triggers,
            "conditions": decision.conditions,
            "endorsements": decision.endorsements,
            "citations": decision.citations,
            "evidence_map": decision.evidence_map
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Underwriting decision error: {e}")
        raise HTTPException(status_code=500, detail=f"Underwriting decision failed: {str(e)}")


@router.get("/documents")
async def get_document_summary():
    """
    Get summary of ingested documents
    
    Returns:
        Document summary with chunk counts
    """
    try:
        rag = get_rag_engine()
        summary = rag.get_document_summary()
        
        return {
            "documents": summary,
            "total_documents": len(summary),
            "total_chunks": sum(info["chunk_count"] for info in summary.values())
        }
        
    except Exception as e:
        logger.error(f"Document summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Document summary failed: {str(e)}")


@router.get("/evidence/{chunk_id}")
async def get_evidence_details(chunk_id: str):
    """
    Get detailed evidence for a specific chunk
    
    Args:
        chunk_id: Unique chunk identifier
        
    Returns:
        Detailed chunk information
    """
    try:
        rag = get_rag_engine()
        
        # Search for specific chunk
        chunks = rag.retrieve(f"chunk_id:{chunk_id}", n_results=1)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        chunk = chunks[0]
        
        return {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "doc_title": chunk.metadata.get("doc_title", "Unknown"),
            "section": chunk.section,
            "subsection": chunk.metadata.get("subsection", ""),
            "text": chunk.text,
            "relevance_score": chunk.relevance_score,
            "metadata": chunk.metadata,
            "full_context": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evidence details error: {e}")
        raise HTTPException(status_code=500, detail=f"Evidence details failed: {str(e)}")


@router.post("/highlight-document")
async def highlight_document(request: Dict[str, Any]):
    """
    Generate document highlighting information
    
    Args:
        request: Document highlighting request
        
    Returns:
        Highlighting data for document viewer
    """
    try:
        chunk_ids = request.get("chunk_ids", [])
        
        if not chunk_ids:
            return {"highlights": [], "total": 0}
        
        rag = get_rag_engine()
        highlights = []
        
        for chunk_id in chunk_ids:
            chunks = rag.retrieve(f"chunk_id:{chunk_id}", n_results=1)
            if chunks:
                chunk = chunks[0]
                highlights.append({
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "rule_strength": chunk.metadata.get("rule_strength", "informational"),
                    "section": chunk.section,
                    "doc_title": chunk.metadata.get("doc_title", "Unknown"),
                    "highlight_class": f"highlight-{chunk.metadata.get('rule_strength', 'informational')}"
                })
        
        return {
            "highlights": highlights,
            "total": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"Document highlighting error: {e}")
        raise HTTPException(status_code=500, detail=f"Document highlighting failed: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Check RAG system health
    
    Returns:
        System health status
    """
    try:
        rag = get_rag_engine()
        verifier = get_evidence_verifier()
        composer = get_decision_composer()
        
        # Test basic functionality
        test_chunks = rag.retrieve("test", n_results=1)
        
        return {
            "status": "healthy",
            "components": {
                "rag_engine": "operational",
                "evidence_verifier": "operational",
                "decision_composer": "operational"
            },
            "documents_processed": len(rag.documents),
            "total_chunks": len(rag.chunks),
            "test_retrieval": len(test_chunks) > 0
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "components": {
                "rag_engine": "error",
                "evidence_verifier": "unknown",
                "decision_composer": "unknown"
            }
        }
