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
import sqlite3

from config import settings

# Import database for persistent storage
from storage.database import UnderwritingDB, get_db

# Import schemas
from models.schemas import HumanReviewRecord, QuoteRecord

# Database-backed storage for human review approvals
# Note: Using database instead of in-memory storage for persistence

# Import message queue (Redis-based)
from app.redis_queue import redis_message_queue, MessagePriority, process_quote_async

# Import rate limiting
from security import create_rate_limiter

logger = logging.getLogger(__name__)

# Initialize rate limiter
rate_limiter = create_rate_limiter()

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
    
    # Include Verisk mock API router
    from app.verisk_mock import router as verisk_router
    app.include_router(verisk_router)
    
    # Import PDF parser for property data
    from app.pdf_parser import initialize_property_cache, get_property_cache
    
    # Startup event for initialization
    @app.on_event("startup")
    async def startup_event():
        # Initialize property cache from PDF
        logger.info("Initializing property cache from PDF...")
        cache_success = initialize_property_cache()
        if cache_success:
            property_cache = get_property_cache()
            logger.info(f"Property cache initialized with {property_cache.get_property_count()} properties")
        else:
            logger.warning("Failed to initialize property cache from PDF")
    
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
                "review_status": "/quote/{run_id}/review-status",
                "properties": "/properties",
                "properties/search": "/properties/search",
                "properties/stats": "/properties/stats"
            }
        }
    
    @app.post("/quote/run")
    async def run_quote_processing(request: Dict[str, Any]):
        """
        Process a quote through underwriting workflow.
        """
        # Apply rate limiting
        if rate_limiter:
            # Simple IP-based rate limiting for demo
            # In production, use proper request context
            client_ip = "127.0.0.1"  # Would get from request.client.host
            allowed, info = rate_limiter.is_allowed(f"quote_submit:{client_ip}", limit=10, window=60)
            if not allowed:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {info.get('reset_time', 60)} seconds."
                )
        
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
            
            # Validate coverage amount is a positive number
            try:
                coverage_amount = float(submission.get("coverage_amount", 0))
                if coverage_amount <= 0:
                    raise HTTPException(status_code=400, detail="Coverage amount must be greater than 0")
                if coverage_amount > 10000000:  # $10M max limit
                    raise HTTPException(status_code=400, detail="Coverage amount exceeds maximum limit of $10,000,000")
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Coverage amount must be a valid number")
            
            # Validate applicant name
            applicant_name = submission.get("applicant_name", "").strip()
            if len(applicant_name) < 2 or len(applicant_name) > 100:
                raise HTTPException(status_code=400, detail="Applicant name must be between 2 and 100 characters")
            
            # Validate address
            address = submission.get("address", "").strip()
            if len(address) < 5 or len(address) > 500:
                raise HTTPException(status_code=400, detail="Address must be between 5 and 500 characters")
            
            # Validate property type if provided
            if "property_type" in submission:
                valid_types = ["single_family", "condo", "townhome", "multi_family", "commercial"]
                property_type = submission["property_type"].lower().strip()
                if property_type not in valid_types:
                    raise HTTPException(status_code=400, detail=f"Property type must be one of: {', '.join(valid_types)}")
            
            # Validate construction year if provided
            if "construction_year" in submission and submission["construction_year"]:
                try:
                    year = int(submission["construction_year"])
                    current_year = datetime.now().year
                    if year < 1800 or year > current_year + 5:
                        raise HTTPException(status_code=400, detail=f"Construction year must be between 1800 and {current_year + 5}")
                except (ValueError, TypeError):
                    raise HTTPException(status_code=400, detail="Construction year must be a valid year")
            
            # Validate square footage if provided
            if "square_footage" in submission and submission["square_footage"]:
                try:
                    sqft = float(submission["square_footage"])
                    if sqft <= 0 or sqft > 50000:
                        raise HTTPException(status_code=400, detail="Square footage must be between 0 and 50,000")
                except (ValueError, TypeError):
                    raise HTTPException(status_code=400, detail="Square footage must be a valid number")
            
            # Check for RCE data and adjust coverage if needed
            address = submission.get("address", "")
            original_coverage = coverage_amount
            adjusted_coverage = coverage_amount
            rce_data = None
            
            logger.info(f"Processing quote submission for address: {address}, coverage: ${original_coverage:,}")
            
            if address:
                try:
                    # Search for property by address
                    property_cache = get_property_cache()
                    property_record = property_cache.find_property_by_address(address)
                    
                    if property_record and property_record.replacement_cost_estimate:
                        rce_data = {
                            "rce": property_record.replacement_cost_estimate,
                            "property_type": property_record.property_type,
                            "year_built": property_record.year_built,
                            "square_footage": property_record.square_footage,
                            "wildfire_risk": property_record.wildfire_risk,
                            "flood_risk": property_record.flood_risk
                        }
                        
                        # Adjust coverage if RCE is higher
                        if property_record.replacement_cost_estimate > original_coverage:
                            adjusted_coverage = property_record.replacement_cost_estimate
                            logger.info(f"Coverage adjusted from ${original_coverage:,} to ${adjusted_coverage:,} based on RCE for {address}")
                        else:
                            logger.info(f"Coverage ${original_coverage:,} accepted (RCE: ${property_record.replacement_cost_estimate:,})")
                    else:
                        logger.warning(f"No RCE data found for address: {address}")
                        
                except (AttributeError, KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to lookup RCE for address {address}: {e}")
            
            # Simulate processing
            run_id = str(uuid.uuid4())
            
            # Mock decision based on adjusted coverage amount
            coverage = adjusted_coverage
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
            
            # Add RCE adjustment information if applicable
            rce_adjustment = None
            if rce_data and adjusted_coverage != original_coverage:
                rce_adjustment = {
                    "original_coverage": original_coverage,
                    "adjusted_coverage": adjusted_coverage,
                    "coverage_increased": True,
                    "increase_amount": adjusted_coverage - original_coverage,
                    "rce_data": rce_data
                }
            
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
                "rce_adjustment": rce_adjustment,
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
            
            # Save quote record to database
            db_instance = get_db()
            quote_record = QuoteRecord(
                run_id=run_id,
                status="completed",
                timestamp=datetime.now(),
                message=response["message"],
                processing_time_ms=response["processing_time_ms"],
                submission=submission,
                decision=response["decision"],
                premium=response["premium"],
                rce_adjustment=response["rce_adjustment"],
                requires_human_review=response["requires_human_review"],
                human_review_details=response["human_review_details"],
                required_questions=response["required_questions"],
                citations=response["citations"]
            )
            db_instance.save_quote_record(quote_record)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {str(e)}"
            )
    
    @app.get("/runs")
    async def list_runs(limit: int = 100, offset: int = 0):
        """
        List recent runs with pagination from database.
        """
        try:
            db_instance = get_db()
            
            # Get quote records from database
            with sqlite3.connect(db_instance.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT run_id, status, timestamp, message, processing_time_ms, "
                    "submission, decision, premium, requires_human_review "
                    "FROM quote_records "
                    "ORDER BY timestamp DESC "
                    "LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                rows = cursor.fetchall()
                
                # Get total count
                total_count = conn.execute(
                    "SELECT COUNT(*) FROM quote_records"
                ).fetchone()[0]
            
            # Convert to response format
            runs = []
            for row in rows:
                try:
                    submission = json.loads(row["submission"]) if row["submission"] else {}
                    decision = json.loads(row["decision"]) if row["decision"] else {}
                    premium = json.loads(row["premium"]) if row["premium"] else {}
                    
                    runs.append({
                        "run_id": row["run_id"],
                        "status": row["status"],
                        "created_at": row["timestamp"],
                        "updated_at": row["timestamp"],
                        "applicant_name": submission.get("applicant_name", "Unknown"),
                        "address": submission.get("address", "Unknown"),
                        "property_type": submission.get("property_type", "unknown"),
                        "coverage_amount": submission.get("coverage_amount", 0),
                        "decision": decision,
                        "premium": premium,
                        "requires_human_review": bool(row["requires_human_review"]),
                        "processing_time_ms": row["processing_time_ms"]
                    })
                except json.JSONDecodeError as e:
                    # Skip malformed records
                    continue
            
            return {
                "runs": runs,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            # If database fails, return empty response rather than mock data
            return {
                "runs": [],
                "total_count": 0,
                "limit": limit,
                "offset": offset,
                "error": f"Database error: {str(e)}"
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
    
    @app.get("/quote/{run_id}/details")
    async def get_quote_details(run_id: str):
        """
        Get detailed quote information from database.
        """
        try:
            db_instance = get_db()
            quote_record = db_instance.get_quote_record(run_id)
            
            if not quote_record:
                raise HTTPException(status_code=404, detail="Quote not found")
            
            # Get human review status if available
            review_record = db_instance.get_human_review_record(run_id)
            
            return {
                "run_id": quote_record.run_id,
                "status": quote_record.status,
                "timestamp": quote_record.timestamp.isoformat(),
                "message": quote_record.message,
                "processing_time_ms": quote_record.processing_time_ms,
                "applicant_name": quote_record.submission.get("applicant_name"),
                "address": quote_record.submission.get("address"),
                "property_type": quote_record.submission.get("property_type"),
                "coverage_amount": quote_record.submission.get("coverage_amount"),
                "construction_year": quote_record.submission.get("construction_year"),
                "square_footage": quote_record.submission.get("square_footage"),
                "decision": quote_record.decision,
                "premium": quote_record.premium,
                "rce_adjustment": quote_record.rce_adjustment,
                "requires_human_review": quote_record.requires_human_review,
                "human_review_details": quote_record.human_review_details,
                "required_questions": quote_record.required_questions,
                "citations": quote_record.citations,
                "review_status": review_record.status if review_record else None,
                "final_decision": review_record.final_decision if review_record else None,
                "reviewer": review_record.reviewer if review_record else None,
                "approved_premium": review_record.approved_premium if review_record else None,
                "review_timestamp": review_record.review_timestamp.isoformat() if review_record and review_record.review_timestamp else None,
                "reviewer_notes": review_record.reviewer_notes if review_record else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving quote details: {str(e)}")
    
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
            # Store approval data
            approval_record = {
                "run_id": run_id,
                "status": "human_approved",
                "original_decision": "REFER",
                "final_decision": approval_data.get("final_decision", "REFER"),
                "reviewer_notes": approval_data.get("reviewer_notes", ""),
                "approved_premium": approval_data.get("approved_premium", 0),
                "reviewer": approval_data.get("reviewer_name", "Human Reviewer"),
                "review_timestamp": datetime.now().isoformat(),
                "submission_timestamp": datetime.now().isoformat()
            }
            
            # Store in database for persistence
            db_instance = get_db()
            review_record = HumanReviewRecord(
                run_id=run_id,
                status="human_approved",
                requires_human_review=True,
                final_decision=approval_data.get("final_decision", "REFER"),
                reviewer=approval_data.get("reviewer_name", "Human Reviewer"),
                review_timestamp=datetime.now(),
                approved_premium=approval_data.get("approved_premium", 0),
                reviewer_notes=approval_data.get("reviewer_notes", ""),
                review_priority="high",
                assigned_reviewer=approval_data.get("reviewer_name", "Human Reviewer"),
                estimated_review_time="30 minutes",
                submission_timestamp=datetime.now(),
                review_deadline=datetime.now() + timedelta(hours=24)
            )
            db_instance.save_human_review_record(review_record)
            
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
        db_instance = get_db()
        review_record = db_instance.get_human_review_record(run_id)
        
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
    
    # Properties endpoints
    @app.get("/properties")
    async def get_all_properties():
        """Get all properties from PDF cache"""
        try:
            property_cache = get_property_cache()
            properties = property_cache.get_all_properties()
            
            return {
                "properties": [
                    {
                        "address": prop.address,
                        "property_type": prop.property_type,
                        "year_built": prop.year_built,
                        "square_footage": prop.square_footage,
                        "replacement_cost_estimate": prop.replacement_cost_estimate,
                        "wildfire_risk": prop.wildfire_risk,
                        "flood_risk": prop.flood_risk
                    }
                    for prop in properties
                ],
                "total_count": len(properties),
                "source": "pdf_cache"
            }
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get properties: {str(e)}")
    
    @app.get("/properties/search")
    async def search_properties(query: str = "", limit: int = 10):
        """Search properties by address"""
        try:
            property_cache = get_property_cache()
            properties = property_cache.get_all_properties()
            
            # Filter properties by address query
            if query:
                query_lower = query.lower()
                filtered_properties = [
                    prop for prop in properties
                    if query_lower in prop.address.lower()
                ]
            else:
                filtered_properties = properties
            
            # Limit results
            limited_properties = filtered_properties[:limit]
            
            return {
                "properties": [
                    {
                        "address": prop.address,
                        "property_type": prop.property_type,
                        "year_built": prop.year_built,
                        "square_footage": prop.square_footage,
                        "replacement_cost_estimate": prop.replacement_cost_estimate,
                        "wildfire_risk": prop.wildfire_risk,
                        "flood_risk": prop.flood_risk
                    }
                    for prop in limited_properties
                ],
                "query": query,
                "total_found": len(filtered_properties),
                "returned_count": len(limited_properties),
                "limit": limit
            }
        except Exception as e:
            logger.error(f"Error searching properties: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to search properties: {str(e)}")
    
    @app.get("/properties/stats")
    async def get_property_stats():
        """Get property statistics"""
        try:
            property_cache = get_property_cache()
            properties = property_cache.get_all_properties()
            
            # Calculate statistics
            total_properties = len(properties)
            property_types = {}
            risk_levels = {"LOW": 0, "MODERATE": 0, "HIGH": 0}
            
            for prop in properties:
                # Count by property type
                prop_type = prop.property_type
                property_types[prop_type] = property_types.get(prop_type, 0) + 1
                
                # Count by risk level
                overall_risk = prop.wildfire_risk  # Using wildfire risk as overall
                if overall_risk in risk_levels:
                    risk_levels[overall_risk] += 1
            
            return {
                "total_properties": total_properties,
                "property_types": property_types,
                "risk_distribution": risk_levels,
                "average_replacement_cost": sum(prop.replacement_cost_estimate for prop in properties) / total_properties if total_properties > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting property stats: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get property stats: {str(e)}")
    
    return app
