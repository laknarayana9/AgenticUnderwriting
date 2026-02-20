from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from models.schemas import (
    QuoteSubmission, RunRecord, RunStatusResponse, 
    QuoteRunRequest, QuoteRunResponse, RunListResponse,
    WorkflowState
)
from workflows.graph import run_underwriting_workflow
from workflows.agentic_graph import run_agentic_underwriting_workflow
from storage.database import db
from config import settings
from metrics_dashboard import create_dashboard_routes

# Initialize FastAPI app
app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add dashboard routes
create_dashboard_routes(app)


def store_run_record(workflow_state: WorkflowState, status: str = "completed", error_message: Optional[str] = None):
    """
    Store the workflow result in the database.
    """
    run_id = str(uuid.uuid4())
    
    # Create node outputs for audit trail
    node_outputs = {
        "validation": {
            "missing_info": workflow_state.missing_info,
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "validate_submission"]
        },
        "enrichment": {
            "normalized_address": workflow_state.enrichment_result.normalized_address.model_dump() if workflow_state.enrichment_result else None,
            "hazard_scores": workflow_state.enrichment_result.hazard_scores.model_dump() if workflow_state.enrichment_result else None,
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name in ["address_normalize", "hazard_score"]]
        },
        "retrieval": {
            "guidelines_count": len(workflow_state.retrieved_guidelines),
            "citations": [chunk.doc_id for chunk in workflow_state.retrieved_guidelines],
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "rag_retrieval"]
        },
        "assessment": {
            "eligibility_score": workflow_state.uw_assessment.eligibility_score if workflow_state.uw_assessment else None,
            "triggers": [t.model_dump() for t in workflow_state.uw_assessment.triggers] if workflow_state.uw_assessment else [],
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "underwriting_assessment"]
        },
        "rating": {
            "premium": workflow_state.premium_breakdown.model_dump() if workflow_state.premium_breakdown else None,
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "rating_calculation"]
        },
        "decision": {
            "decision": workflow_state.decision.decision if workflow_state.decision else None,
            "rationale": workflow_state.decision.rationale if workflow_state.decision else None,
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "decision_making"]
        }
    }
    
    run_record = RunRecord(
        run_id=run_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=status,
        workflow_state=workflow_state,
        node_outputs=node_outputs,
        error_message=error_message
    )
    
    db.save_run_record(run_record)
    return run_id


@app.post("/quote/run", response_model=QuoteRunResponse)
async def run_quote_processing(request: QuoteRunRequest):
    """
    Process a quote submission through the underwriting workflow.
    """
    try:
        # Choose workflow based on agentic flag
        if request.use_agentic:
            workflow_state = run_agentic_underwriting_workflow(
                request.submission.model_dump(), 
                request.additional_answers
            )
        else:
            workflow_state = run_underwriting_workflow(request.submission.model_dump())
        
        # Store the run record
        run_id = store_run_record(workflow_state)
        
        # Prepare response
        decision_dict = workflow_state.decision.model_dump() if workflow_state.decision else None
        premium_dict = workflow_state.premium_breakdown.model_dump() if workflow_state.premium_breakdown else None
        citations = workflow_state.uw_assessment.citations if workflow_state.uw_assessment else []
        required_questions = [q.model_dump() for q in workflow_state.decision.required_questions] if workflow_state.decision and workflow_state.decision.required_questions else []
        
        # Determine message based on decision
        if workflow_state.decision:
            if workflow_state.decision.decision == "ACCEPT":
                message = "Quote accepted for policy issuance"
            elif workflow_state.decision.decision == "REFER":
                message = "Quote referred for manual review"
            elif workflow_state.decision.decision == "DECLINE":
                message = "Quote declined"
            else:
                message = "Processing complete"
        else:
            message = "Processing complete"
        
        return QuoteRunResponse(
            run_id=run_id,
            status="completed",
            decision=decision_dict,
            premium=premium_dict,
            citations=citations,
            required_questions=required_questions,
            message=message
        )
        
    except Exception as e:
        # Create a failed run record
        error_state = WorkflowState(quote_submission=request.submission)
        run_id = store_run_record(error_state, status="failed", error_message=str(e))
        
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """
    Get the status and details of a specific run.
    """
    run_record = db.get_run_record(run_id)
    
    if run_record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatusResponse(
        run_id=run_record.run_id,
        status=run_record.status,
        created_at=run_record.created_at,
        updated_at=run_record.updated_at,
        workflow_state=run_record.workflow_state.model_dump(),
        error_message=run_record.error_message
    )


@app.get("/runs", response_model=RunListResponse)
async def list_runs(limit: int = 50, status: Optional[str] = None):
    """
    List recent runs with optional status filter.
    """
    runs = db.list_runs(limit=limit, status=status)
    
    return RunListResponse(
        runs=runs,
        total_count=len(runs)
    )


@app.get("/runs/{run_id}/audit")
async def get_run_audit(run_id: str):
    """
    Get the full audit trail for a run including all node outputs.
    """
    run_record = db.get_run_record(run_id)
    
    if run_record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "run_id": run_record.run_id,
        "status": run_record.status,
        "created_at": run_record.created_at,
        "updated_at": run_record.updated_at,
        "workflow_state": run_record.workflow_state.model_dump(),
        "node_outputs": run_record.node_outputs,
        "tool_calls": [call.model_dump() for call in run_record.workflow_state.tool_calls],
        "error_message": run_record.error_message
    }


@app.get("/stats")
async def get_statistics():
    """
    Get basic statistics about the system.
    """
    return db.get_statistics()


@app.get("/")
async def root():
    """
    Root endpoint that serves the UI.
    """
    return {"message": "Agentic Quote-to-Underwrite API", "ui_url": "/static/index.html"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
