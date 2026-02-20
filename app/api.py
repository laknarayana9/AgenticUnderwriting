"""
API routes separated to avoid circular imports.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from models.schemas import (
    QuoteRunRequest, QuoteRunResponse, RunStatusResponse, 
    RunListResponse, WorkflowState
)
from security import get_current_user, InputValidator
from monitoring import logger, perf_monitor
from storage.database import db


# Create router
router = APIRouter()


@router.post("/run")
async def run_quote_processing(
    request: QuoteRunRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Process a quote through the underwriting workflow.
    """
    perf_monitor.start_timer("quote_processing")
    
    try:
        # Input validation
        validator = InputValidator()
        
        # Validate submission data
        if hasattr(request.submission, 'applicant_email'):
            if not validator.validate_email(request.submission.applicant_email):
                raise HTTPException(status_code=400, detail="Invalid email address")
        
        if not validator.validate_address(request.submission.address):
            raise HTTPException(status_code=400, detail="Invalid address format")
        
        if not validator.validate_coverage_amount(request.submission.coverage_amount):
            raise HTTPException(status_code=400, detail="Invalid coverage amount")
        
        if request.submission.construction_year:
            if not validator.validate_year(request.submission.construction_year):
                raise HTTPException(status_code=400, detail="Invalid construction year")
        
        # Sanitize string inputs
        request.submission.applicant_name = validator.sanitize_string(request.submission.applicant_name)
        request.submission.address = validator.sanitize_string(request.submission.address)
        
        logger.info("Quote processing started", 
                   quote_id=getattr(request, 'quote_id', 'unknown'),
                   use_agentic=request.use_agentic,
                   user_id=current_user.get("user_id") if current_user else None)
        
        # Import workflows lazily to avoid circular imports
        from workflows.graph import run_underwriting_workflow
        from workflows.agentic_graph import run_agentic_underwriting_workflow
        
        # Run the appropriate workflow
        if request.use_agentic:
            workflow_state = await run_agentic_underwriting_workflow(
                request.submission, 
                request.additional_answers
            )
        else:
            workflow_state = await run_underwriting_workflow(request.submission)
        
        # Store the run record
        run_id = store_run_record(workflow_state)
        
        # Prepare response
        decision_dict = workflow_state.decision.model_dump() if workflow_state.decision else None
        premium_dict = workflow_state.premium_breakdown.model_dump() if workflow_state.premium_breakdown else None
        citations = [citation.model_dump() for citation in workflow_state.retrieved_chunks]
        required_questions = workflow_state.missing_info
        message = "Quote processing completed successfully"
        
        response = QuoteRunResponse(
            run_id=run_id,
            status="completed",
            decision=decision_dict,
            premium=premium_dict,
            citations=citations,
            required_questions=required_questions,
            message=message
        )
        
        perf_monitor.end_timer("quote_processing")
        
        logger.info("Quote processing completed", 
                   run_id=run_id,
                   decision=decision_dict.get("decision") if decision_dict else None,
                   duration=perf_monitor.get_stats("quote_processing").get("avg", 0))
        
        return response
        
    except HTTPException:
        perf_monitor.end_timer("quote_processing")
        raise
    except Exception as e:
        perf_monitor.end_timer("quote_processing")
        logger.error("Quote processing failed", 
                    error=str(e),
                    quote_id=getattr(request, 'quote_id', 'unknown'),
                    traceback=str(e.__traceback__))
        
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


def store_run_record(workflow_state: WorkflowState, status: str = "completed", error_message: Optional[str] = None):
    """Store the workflow result in the database."""
    run_id = str(uuid.uuid4())
    
    # Create node outputs for audit trail
    node_outputs = {
        "validation": {
            "missing_info": workflow_state.missing_info,
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "validate_submission"]
        },
        "enrichment": {
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name in ["normalize_address", "calculate_hazard_scores"]]
        },
        "retrieval": {
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "retrieve_guidelines"]
        },
        "assessment": {
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "assess_risk"]
        },
        "rating": {
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "calculate_premium"]
        },
        "decision": {
            "tool_calls": [call.model_dump() for call in workflow_state.tool_calls if call.tool_name == "make_decision"]
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
