#!/usr/bin/env python3
"""
Simple FastAPI server for Phase 2 testing
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import uuid
import random
from datetime import datetime

# Create FastAPI app
app = FastAPI(title="Agentic Quote-to-Underwrite - Phase 2")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve main page"""
    try:
        with open("static/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <body>
            <h1>Agentic Quote-to-Underwrite</h1>
            <p>Error: static/index.html not found</p>
            <p>Please ensure you're running from the project root directory.</p>
        </body>
        </html>
        """)

@app.post("/quote/run")
async def run_quote_processing(request: dict):
    """Mock quote processing with RAG simulation"""
    try:
        submission = request.get("submission", {})
        use_agentic = request.get("use_agentic", False)
        
        # Generate mock decision
        decisions = ["ACCEPT", "REFER", "DECLINE"]
        decision = random.choice(decisions)
        confidence = random.uniform(0.6, 0.95)
        
        # Mock RAG evidence if agentic is enabled
        rag_evidence = []
        rag_assessment = None
        
        if use_agentic:
            # Mock evidence chunks
            rag_evidence = [
                {
                    "chunk_id": f"mock_chunk_{i}",
                    "doc_title": f"Underwriting Guidelines {i+1}",
                    "section": f"Section {i+1}",
                    "text": f"Mock evidence text for {decision} decision based on underwriting rules...",
                    "relevance_score": random.uniform(0.7, 0.95),
                    "rule_strength": random.choice(["mandatory", "required", "recommended"])
                }
                for i in range(3)
            ]
            
            rag_assessment = {
                "assessment": {
                    "quality": random.choice(["high", "medium", "low"]),
                    "confidence": confidence,
                    "rule_strength": random.choice(["mandatory", "required", "recommended"])
                },
                "chunks_count": len(rag_evidence)
            }
        
        # Mock response
        response = {
            "run_id": str(uuid.uuid4()),
            "status": "completed",
            "decision": {
                "decision": decision,
                "confidence": confidence,
                "reason": f"Mock {decision.lower()} decision based on evidence review"
            },
            "premium": {
                "annual_premium": random.uniform(500, 2000),
                "monthly_premium": random.uniform(40, 170),
                "coverage_amount": submission.get("coverage_amount", 500000)
            },
            "citations": [
                {
                    "doc_title": "Underwriting Guidelines",
                    "text": f"Mock citation for {decision} decision",
                    "relevance_score": random.uniform(0.8, 0.95)
                }
            ],
            "required_questions": [
                {
                    "question": "Please provide additional documentation",
                    "description": "Required for underwriting review"
                }
            ] if decision == "REFER" else [],
            "referral_triggers": [f"Mock trigger for {decision}"],
            "conditions": [f"Mock condition for {decision}"],
            "rag_evidence": rag_evidence,
            "rag_assessment": rag_assessment,
            "requires_human_review": decision in ["REFER", "DECLINE"],
            "human_review_details": {
                "review_type": "mock_review",
                "assigned_reviewer": "underwriting_team",
                "review_priority": "high" if decision in ["REFER", "DECLINE"] else "low",
                "estimated_review_time": "24-48 hours" if decision in ["REFER", "DECLINE"] else "N/A"
            },
            "message": f"Quote processing completed - {decision}",
            "processing_time_ms": random.randint(100, 300)
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote processing failed: {str(e)}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "phase": "2"}

@app.get("/runs")
async def get_runs(limit: int = 100):
    """Get recent runs for display"""
    # Mock recent runs data
    mock_runs = [
        {
            "run_id": f"mock_run_{i}",
            "status": random.choice(["completed", "pending", "referred"]),
            "decision": {
                "decision": random.choice(["ACCEPT", "REFER", "DECLINE"]),
                "confidence": round(random.uniform(0.6, 0.95), 3)
            },
            "created_at": datetime.now().isoformat(),
            "premium": {
                "annual_premium": round(random.uniform(500, 2000), 2),
                "coverage_amount": random.choice([300000, 500000, 750000])
            }
        }
        for i in range(10)  # Generate 10 mock runs
    ]
    
    return {
        "runs": mock_runs[:limit],
        "total_count": len(mock_runs)
    }

@app.get("/templates/evidence-panel.html")
async def get_evidence_panel():
    """Serve evidence panel template"""
    try:
        with open("templates/evidence-panel.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <body>
            <h1>Evidence Panel Template</h1>
            <p>Error: templates/evidence-panel.html not found</p>
        </body>
        </html>
        """)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Phase 2 Evidence-First Underwriting Server")
    print("🌐 Server will be available at: http://localhost:8000")
    print("📄 Main page: http://localhost:8000/")
    print("🎯 Ready for testing!")
    uvicorn.run("simple_server:app", host="0.0.0.0", port=8000, reload=True)
