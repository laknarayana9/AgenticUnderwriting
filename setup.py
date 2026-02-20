#!/usr/bin/env python3
"""
Setup script for Agentic Quote-to-Underwrite system.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*50)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✅ Success!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    """Run the complete setup."""
    print("🚀 Setting up Agentic Quote-to-Underwrite System")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version}")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create necessary directories
    directories = ["storage", "storage/chroma_db"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Initialize RAG documents
    print("\n📚 Initializing RAG system...")
    try:
        from app.rag_engine import RAGEngine
        rag = RAGEngine()
        rag.ingest_documents(force_reingest=True)
        print("✅ RAG system initialized with guideline documents")
        
        # Show document summary
        summary = rag.get_document_summary()
        print(f"📄 Ingested {len(summary)} documents:")
        for doc_id, info in summary.items():
            print(f"  - {doc_id}: {info['chunk_count']} chunks, {len(info['sections'])} sections")
    
    except Exception as e:
        print(f"❌ Error initializing RAG: {e}")
        sys.exit(1)
    
    # Test the setup
    print("\n🧪 Testing setup...")
    try:
        from workflows.graph import run_underwriting_workflow
        from models.schemas import QuoteSubmission
        
        # Create a test submission
        test_submission = QuoteSubmission(
            applicant_name="Test User",
            address="123 Test St, Test City, CA 90210",
            property_type="single_family",
            coverage_amount=250000,
            construction_year=2000
        )
        
        # Run workflow
        result = run_underwriting_workflow(test_submission.model_dump())
        print("✅ Workflow test completed successfully")
        print(f"📊 Decision: {result.decision.decision if result.decision else 'No decision'}")
        
    except Exception as e:
        print(f"❌ Error testing workflow: {e}")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("🎉 Setup completed successfully!")
    print("="*50)
    print("\n📋 Next steps:")
    print("1. Start the API server:")
    print("   python -m app.main")
    print("\n2. Open the web UI:")
    print("   http://localhost:8000/static/index.html")
    print("\n3. Or test with the API:")
    print("   python test_api.py")
    print("\n4. API Documentation:")
    print("   http://localhost:8000/docs")
    print("\n🔧 Environment variables (optional):")
    print("   OPENAI_API_KEY=your_key_here")
    print("   DATABASE_URL=sqlite:///./underwriting.db")

if __name__ == "__main__":
    main()
