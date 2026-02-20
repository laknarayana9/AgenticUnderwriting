"""
Run management routes separated to avoid circular imports.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import RunStatusResponse, RunListResponse
from storage.database import db
from monitoring import logger


# Create router
router = APIRouter()


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """
    Get status and details of a specific run.
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


@router.get("/", response_model=RunListResponse)
async def list_runs(limit: int = 50, offset: int = 0):
    """
    List recent runs with pagination.
    """
    runs = db.list_runs(limit=limit, offset=offset)
    total_count = db.get_run_count()
    
    return RunListResponse(
        runs=runs,
        total_count=total_count
    )


@router.get("/{run_id}/audit")
async def get_run_audit(run_id: str):
    """
    Get detailed audit trail for a specific run.
    """
    run_record = db.get_run_record(run_id)
    
    if run_record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "run_id": run_record.run_id,
        "created_at": run_record.created_at,
        "updated_at": run_record.updated_at,
        "status": run_record.status,
        "tool_calls": run_record.workflow_state.tool_calls,
        "node_outputs": run_record.node_outputs,
        "error_message": run_record.error_message
    }


@router.get("/{run_id}/trace")
async def get_run_trace(run_id: str):
    """
    Get execution trace for a specific run.
    """
    run_record = db.get_run_record(run_id)
    
    if run_record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Build trace data
    timeline = []
    for tool_call in run_record.workflow_state.tool_calls:
        timeline.append({
            "timestamp": tool_call.timestamp,
            "tool": tool_call.tool_name,
            "duration_ms": getattr(tool_call, 'execution_time_ms', None),
            "status": "completed"
        })
    
    return {
        "run_id": run_record.run_id,
        "timeline": timeline,
        "workflow_state": run_record.workflow_state.model_dump(),
        "node_outputs": run_record.node_outputs
    }
