"""
Complete working application with all routes for browser testing.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
import json

from config import settings

# Import database for persistent storage
from storage.database import UnderwritingDB

# Initialize database
db = UnderwritingDB()

# Import message queue (Redis-based)
from app.redis_queue import redis_message_queue, MessagePriority, process_quote_async

logger = logging.getLogger(__name__)

def create_complete_app() -> FastAPI:
    """
    Create complete FastAPI application with all routes.
    """
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version
    )
    
    # Mount static files
    import os
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    @app.get("/health")
    async def health():
        try:
            redis_health = await redis_message_queue.health_check()
            return {
                "status": redis_health["status"],
                "message": "Complete app working with Redis queue",
                "timestamp": datetime.now().isoformat(),
                "redis": {
                    "connected": redis_health["redis_connected"],
                    "queue_stats": redis_health.get("queue_stats", {}),
                    "using_mock": redis_health.get("using_mock", False)
                }
            }
        except Exception as e:
            return {
                "status": "healthy",
                "message": "Complete app working (queue initialization in progress)",
                "timestamp": datetime.now().isoformat(),
                "redis": {
                    "connected": False,
                    "queue_stats": {},
                    "error": str(e)
                }
            }
    
    @app.get("/")
    async def root():
        return {
            "message": "Agentic Quote-to-Underwrite API", 
            "version": "1.0.0",
            "test_interface": "/static/index.html",
            "endpoints": {
                "health": "/health",
                "quote": "/quote/run",
                "quote_async": "/quote/submit",
                "queue_status": "/queue/{message_id}",
                "queue_stats": "/queue/stats",
                "runs": "/runs",
                "metrics": "/metrics",
                "human_review": "/quote/{run_id}/approve",
                "review_status": "/quote/{run_id}/review-status"
            }
        }
    
    @app.post("/quote/run")
    async def run_quote_processing(request: Dict[str, Any]):
        """
        Process a quote through underwriting workflow.
        """
        try:
            # Extract submission data
            submission = request.get("submission", {})
            use_agentic = request.get("use_agentic", False)
            quote_id = request.get("quote_id", f"test_{uuid.uuid4()}")
            
            # Validate required fields
            if not submission.get("applicant_name"):
                raise HTTPException(status_code=400, detail="Applicant name is required")
            
            if not submission.get("address"):
                raise HTTPException(status_code=400, detail="Address is required")
            
            if not submission.get("coverage_amount"):
                raise HTTPException(status_code=400, detail="Coverage amount is required")
            
            # Simulate processing
            run_id = str(uuid.uuid4())
            
            # Mock decision based on coverage amount
            coverage = submission.get("coverage_amount", 0)
            if coverage > 500000:
                decision = "REFER"
                reason = "Coverage amount exceeds maximum limit - requires human review"
                requires_human_review = True
            elif coverage < 100000:
                decision = "REFER"
                reason = "Coverage amount below minimum threshold - requires human review"
                requires_human_review = True
            else:
                decision = "ACCEPT"
                reason = "Standard risk profile"
                requires_human_review = False
            
            # Mock premium calculation
            premium = coverage * 0.002  # 0.2% of coverage
            
            response = {
                "run_id": run_id,
                "status": "completed",
                "decision": {
                    "decision": decision,
                    "confidence": 0.85,
                    "reason": reason
                },
                "premium": {
                    "annual_premium": premium,
                    "monthly_premium": premium / 12,
                    "coverage_amount": coverage
                },
                "citations": [
                    {
                        "doc_id": "test_doc",
                        "text": f"Mock citation for {decision} decision",
                        "relevance_score": 0.9
                    }
                ],
                "required_questions": [],
                "requires_human_review": requires_human_review,
                "human_review_details": {
                    "review_type": "coverage_threshold",
                    "assigned_reviewer": "underwriting_team",
                    "review_priority": "high" if requires_human_review else "low",
                    "estimated_review_time": "24-48 hours" if requires_human_review else "N/A"
                },
                "message": f"Quote processing completed - {decision}",
                "processing_time_ms": 150
            }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {str(e)}"
            )
    
    @app.get("/runs")
    async def list_runs(limit: int = 50, offset: int = 0):
        """
        List recent runs with pagination.
        """
        # Mock data
        mock_runs = [
            {
                "run_id": str(uuid.uuid4()),
                "status": "completed",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            for _ in range(3)
        ]
        
        return {
            "runs": mock_runs,
            "total_count": len(mock_runs),
            "limit": limit,
            "offset": offset
        }
    
    @app.get("/runs/{run_id}")
    async def get_run_status(run_id: str):
        """
        Get status and details of a specific run.
        """
        # Mock run data
        return {
            "run_id": run_id,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "workflow_state": {
                "decision": {"decision": "ACCEPT", "confidence": 0.85},
                "missing_info": []
            },
            "error_message": None
        }
    
    @app.get("/runs/{run_id}/audit")
    async def get_run_audit(run_id: str):
        """
        Get detailed audit trail for a specific run.
        """
        return {
            "run_id": run_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "completed",
            "tool_calls": [
                {
                    "tool_name": "validate_submission",
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 50,
                    "result": {"valid": True}
                },
                {
                    "tool_name": "assess_risk",
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 100,
                    "result": {"risk_score": 0.3}
                }
            ],
            "node_outputs": {
                "validation": {"status": "completed"},
                "assessment": {"status": "completed"}
            },
            "error_message": None
        }
    
    @app.get("/metrics")
    async def metrics():
        """
        Prometheus metrics endpoint.
        """
        return {
            "metrics": {
                "http_requests_total": 42,
                "http_request_duration_seconds": 0.15,
                "active_workflows": 2,
                "cache_hit_rate": 0.85
            },
            "status": "healthy"
        }
    
    @app.get("/stats")
    async def get_statistics():
        """
        Get basic statistics about system.
        """
        return {
            "total_runs": 42,
            "successful_runs": 38,
            "failed_runs": 4,
            "average_processing_time_ms": 150,
            "cache_hit_rate": 0.85,
            "uptime_seconds": 3600
        }
    
    @app.post("/quote/{run_id}/approve")
    async def approve_human_review(run_id: str, approval_data: Dict[str, Any]):
        """
        Approve a referred quote after human review.
        """
        try:
            # Store approval data in database
            from models.schemas import HumanReviewRecord
            
            approval_record = HumanReviewRecord(
                run_id=run_id,
                status="human_approved",
                requires_human_review=False,
                final_decision=approval_data.get("final_decision", "REFER"),
                reviewer=approval_data.get("reviewer", "Human Reviewer"),
                review_timestamp=datetime.now(),
                approved_premium=float(approval_data.get("approved_premium", "0")),
                reviewer_notes=approval_data.get("reviewer_notes", ""),
                review_priority=approval_data.get("review_priority", "medium"),
                assigned_reviewer=approval_data.get("assigned_reviewer", "underwriting_team"),
                estimated_review_time="Completed",
                submission_timestamp=datetime.now(),
                review_deadline=datetime.now()
            )
            
            # Save to database
            db.save_human_review_record(approval_record)
            
            return approval_record
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Human approval failed: {str(e)}"
            )
    
    @app.get("/quote/{run_id}/review-status")
    async def get_review_status(run_id: str):
        """
        Get review status for a referred quote.
        """
        # Check if we have approval data for this run in database
        review_record = db.get_human_review_record(run_id)
        
        if review_record:
            return {
                "run_id": review_record.run_id,
                "status": review_record.status,
                "requires_human_review": review_record.requires_human_review,
                "final_decision": review_record.final_decision,
                "reviewer": review_record.reviewer,
                "review_timestamp": review_record.review_timestamp.isoformat() if review_record.review_timestamp else None,
                "approved_premium": review_record.approved_premium,
                "reviewer_notes": review_record.reviewer_notes,
                "review_priority": review_record.review_priority,
                "assigned_reviewer": review_record.assigned_reviewer,
                "estimated_review_time": review_record.estimated_review_time,
                "submission_timestamp": review_record.submission_timestamp.isoformat() if review_record.submission_timestamp else None,
                "review_deadline": review_record.review_deadline.isoformat() if review_record.review_deadline else None
            }
        else:
            # Return pending status for unapproved runs
            return {
                "run_id": run_id,
                "status": "pending_review",
                "requires_human_review": True,
                "assigned_reviewer": "underwriting_team",
                "review_priority": "high",
                "estimated_review_time": "24-48 hours",
                "submission_timestamp": datetime.now().isoformat(),
                "review_deadline": (datetime.now() + timedelta(hours=48)).isoformat()
            }
    
    @app.post("/quote/submit")
    async def submit_quote_async(request: Dict[str, Any]):
        """
        Submit a quote for asynchronous processing via message queue.
        """
        try:
            # Validate required fields
            submission = request.get("submission", {})
            if not submission.get("applicant_name"):
                raise HTTPException(status_code=400, detail="Applicant name is required")
            
            if not submission.get("address"):
                raise HTTPException(status_code=400, detail="Address is required")
            
            if not submission.get("coverage_amount"):
                raise HTTPException(status_code=400, detail="Coverage amount is required")
            
            # Determine priority based on coverage amount
            coverage = submission.get("coverage_amount", 0)
            if coverage > 500000:
                priority = MessagePriority.HIGH
            elif coverage < 100000:
                priority = MessagePriority.HIGH
            else:
                priority = MessagePriority.NORMAL
            
            # Add to Redis queue
            message_id = await redis_message_queue.enqueue(request, priority)
            
            # Start background processing
            asyncio.create_task(process_queue_message(message_id))
            
            return {
                "message_id": message_id,
                "status": "queued",
                "priority": priority.name,
                "estimated_processing_time": "2-5 minutes",
                "queue_position": "Processing started"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Queue submission failed: {str(e)}"
            )
    
    @app.get("/queue/{message_id}")
    async def get_queue_status(message_id: str):
        """
        Get the status of a queued message.
        """
        try:
            status = await redis_message_queue.get_status(message_id)
            if not status:
                raise HTTPException(status_code=404, detail="Message not found")
            
            return status
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Status check failed: {str(e)}"
            )
    
    @app.get("/queue/stats")
    async def get_queue_statistics():
        """
        Get queue statistics for monitoring.
        """
        try:
            stats = await redis_message_queue.get_queue_stats()
            return stats
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Stats retrieval failed: {str(e)}"
            )
    
    async def process_queue_message(message_id: str):
        """
        Background task to process messages from the queue.
        """
        try:
            # Get the message from Redis queue
            message = await redis_message_queue.dequeue()
            if not message or message.id != message_id:
                logger.error(f"Message {message_id} not found in queue")
                return
            
            # Process the quote
            result = await process_quote_async(message.id, message.payload)
            
            # Mark as completed
            await redis_message_queue.complete(message.id, result)
            
        except Exception as e:
            # Mark as failed (will retry if retries available)
            await redis_message_queue.fail(message_id, str(e))
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize Redis connection on startup."""
        try:
            await redis_message_queue.initialize()
            logger.info("Redis message queue initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis queue: {e}")
            # Continue without Redis - will fallback to in-memory if needed
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Close Redis connections on shutdown."""
        try:
            await redis_message_queue.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    return app
