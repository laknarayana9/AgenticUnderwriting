#!/usr/bin/env python3
"""
MCP Server for Agentic Underwriting System

This MCP server exposes the underwriting tools and capabilities
as AI-accessible tools that can be used by Claude, GPT, and other AI assistants.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListToolsResult
)

# Import your existing systems
from models.schemas import (
    QuoteSubmission, DecisionType, PremiumBreakdown, 
    WorkflowState, HumanReviewRecord
)
from storage.database import UnderwritingDB
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Initialize logger
logger = logging.getLogger(__name__)

try:
    from app.rag_engine import RAGEngine
except ImportError:
    logger.warning("RAG engine not available, using mock implementation")
    RAGEngine = None

# Mock implementations for MCP tools
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class UnderwritingMCPServer:
    """
    MCP Server that exposes underwriting tools and capabilities.
    """
    
    def __init__(self):
        self.db = UnderwritingDB()
        self.rag_engine = RAGEngine()
        
    async def get_property_risk_assessment(self, address: str) -> Dict[str, Any]:
        """Get risk assessment for a property address."""
        try:
            # Mock hazard scoring based on address patterns
            hazard_scores = {
                "wildfire_risk": 0.3 if "fire" in address.lower() else 0.1,
                "flood_risk": 0.2 if "flood" in address.lower() else 0.05,
                "earthquake_risk": 0.1 if "california" in address.lower() else 0.05,
                "wind_risk": 0.15 if "coastal" in address.lower() else 0.08
            }
            
            return {
                "address": address,
                "hazard_scores": hazard_scores,
                "overall_risk": max(hazard_scores.values()),
                "assessment_date": datetime.now().isoformat(),
                "confidence": 0.85
            }
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {"error": str(e)}
    
    async def calculate_premium(self, coverage_amount: float, property_type: str, 
                         construction_year: int, hazard_scores: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate insurance premium based on various factors."""
        try:
            base_rate = 0.002  # Base rate: $0.20 per $1,000 coverage
            
            # Property type adjustments
            type_multipliers = {
                "single_family": 1.0,
                "condo": 0.8,
                "townhouse": 0.9,
                "commercial": 1.5
            }
            
            # Construction year factor (older = higher risk)
            year_factor = max(0.5, 1.0 - (construction_year - 2000) / 100)
            
            # Hazard adjustment
            hazard_multiplier = 1.0 + (hazard_scores.get("overall_risk", 0) * 0.5)
            
            # Calculate annual premium
            annual_premium = (coverage_amount * base_rate * 
                             type_multipliers.get(property_type, 1.0) * 
                             year_factor * hazard_multiplier)
            
            monthly_premium = annual_premium / 12
            
            return {
                "coverage_amount": coverage_amount,
                "property_type": property_type,
                "construction_year": construction_year,
                "annual_premium": round(annual_premium, 2),
                "monthly_premium": round(monthly_premium, 2),
                "factors": {
                    "base_rate": base_rate,
                    "type_multiplier": type_multipliers.get(property_type, 1.0),
                    "year_factor": year_factor,
                    "hazard_multiplier": hazard_multiplier,
                    "hazard_scores": hazard_scores
                },
                "calculation_date": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in premium calculation: {e}")
            return {"error": str(e)}
    
    async def search_underwriting_guidelines(self, query: str) -> List[Dict[str, Any]]:
        """Search underwriting guidelines using RAG."""
        try:
            if self.rag_engine:
                # Use RAG engine to search guidelines
                results = self.rag_engine.retrieve(query, top_k=3)
                
                formatted_results = []
                for i, result in enumerate(results):
                    formatted_results.append({
                        "chunk_id": result.chunk_id,
                        "section": result.section,
                        "text": result.text,
                        "relevance_score": result.relevance_score,
                        "metadata": result.metadata
                    })
                
                return formatted_results
            else:
                # Mock implementation when RAG engine is not available
                mock_results = [
                    {
                        "chunk_id": f"mock_chunk_{i}",
                        "section": "General Guidelines",
                        "text": f"Mock search result for: {query}",
                        "relevance_score": 0.8,
                        "metadata": {"source": "mock_database"}
                    }
                    for i in range(3)
                ]
                return mock_results
        except Exception as e:
            logger.error(f"Error in guideline search: {e}")
            return [{"error": str(e)}]
    
    async def submit_quote_for_underwriting(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a quote for AI underwriting analysis."""
        try:
            # Generate unique quote ID
            import uuid
            quote_id = str(uuid.uuid4())
            
            # Mock workflow result when agentic workflow is not available
            mock_decision = {
                "decision": "REFER",
                "rationale": "Mock decision - requires human review",
                "citations": ["mock_guideline_1", "mock_guideline_2"]
            }
            
            mock_premium = {
                "annual_premium": 1200.0,
                "monthly_premium": 100.0,
                "base_premium": 1000.0,
                "hazard_surcharge": 200.0
            }
            
            # Store in database with mock data
            from models.schemas import RunRecord, WorkflowState
            workflow_state = WorkflowState(
                quote_submission=QuoteSubmission(**submission),
                decision=mock_decision,
                premium_breakdown=mock_premium
            )
            
            run_record = RunRecord(
                run_id=quote_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                status="completed",
                workflow_state=workflow_state,
                node_outputs={},
                error_message=None
            )
            
            self.db.save_run_record(run_record)
            
            return {
                "quote_id": quote_id,
                "status": "completed",
                "decision": mock_decision,
                "premium": mock_premium,
                "workflow_state": workflow_state.model_dump(),
                "submission": submission,
                "note": "Mock processing - agentic workflow not available"
            }
        except Exception as e:
            logger.error(f"Error in quote submission: {e}")
            return {"error": str(e)}
    
    async def get_quote_status(self, quote_id: str) -> Dict[str, Any]:
        """Get status of a submitted quote."""
        try:
            run_record = self.db.get_run_record(quote_id)
            
            if run_record:
                return {
                    "quote_id": quote_id,
                    "status": run_record.status,
                    "created_at": run_record.created_at.isoformat(),
                    "updated_at": run_record.updated_at.isoformat(),
                    "workflow_state": run_record.workflow_state.model_dump(),
                    "decision": run_record.workflow_state.decision.model_dump() if run_record.workflow_state.decision else None,
                    "premium": run_record.workflow_state.premium_breakdown.model_dump() if run_record.workflow_state.premium_breakdown else None
                }
            else:
                return {
                    "quote_id": quote_id,
                    "status": "not_found",
                    "error": f"Quote {quote_id} not found"
                }
        except Exception as e:
            logger.error(f"Error getting quote status: {e}")
            return {"error": str(e)}
    
    async def get_human_review_status(self, quote_id: str) -> Dict[str, Any]:
        """Get human review status for a quote."""
        try:
            review_record = self.db.get_human_review_record(quote_id)
            
            if review_record:
                return {
                    "quote_id": quote_id,
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
                return {
                    "quote_id": quote_id,
                    "status": "pending_review",
                    "requires_human_review": True,
                    "assigned_reviewer": "underwriting_team",
                    "review_priority": "high",
                    "estimated_review_time": "24-48 hours"
                }
        except Exception as e:
            logger.error(f"Error getting review status: {e}")
            return {"error": str(e)}


# Define MCP tools
TOOLS = [
    Tool(
        name="get_property_risk_assessment",
        description="Get comprehensive risk assessment for a property address including wildfire, flood, earthquake, and wind risks",
        inputSchema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Property address to assess for risks"
                }
            }
        },
        handler=UnderwritingMCPServer.get_property_risk_assessment
    ),
    
    Tool(
        name="calculate_premium",
        description="Calculate insurance premium based on coverage amount, property type, construction year, and hazard scores",
        inputSchema={
            "type": "object",
            "properties": {
                "coverage_amount": {
                    "type": "number",
                    "description": "Insurance coverage amount in dollars"
                },
                "property_type": {
                    "type": "string",
                    "enum": ["single_family", "condo", "townhouse", "commercial"],
                    "description": "Type of property"
                },
                "construction_year": {
                    "type": "integer",
                    "description": "Year property was built"
                },
                "hazard_scores": {
                    "type": "object",
                    "description": "Hazard assessment scores from get_property_risk_assessment"
                }
            }
        },
        handler=UnderwritingMCPServer.calculate_premium
    ),
    
    Tool(
        name="search_underwriting_guidelines",
        description="Search underwriting guidelines and best practices using RAG (Retrieval-Augmented Generation)",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for underwriting guidelines"
                }
            }
        },
        handler=UnderwritingMCPServer.search_underwriting_guidelines
    ),
    
    Tool(
        name="submit_quote_for_underwriting",
        description="Submit a quote for comprehensive AI underwriting analysis using the agentic workflow",
        inputSchema={
            "type": "object",
            "properties": {
                "applicant_name": {
                    "type": "string",
                    "description": "Name of the insurance applicant"
                },
                "address": {
                    "type": "string",
                    "description": "Property address for insurance"
                },
                "property_type": {
                    "type": "string",
                    "enum": ["single_family", "condo", "townhouse", "commercial"],
                    "description": "Type of property"
                },
                "coverage_amount": {
                    "type": "number",
                    "description": "Insurance coverage amount in dollars"
                },
                "construction_year": {
                    "type": "integer",
                    "description": "Year property was built"
                },
                "square_footage": {
                    "type": "number",
                    "description": "Square footage of the property"
                },
                "roof_type": {
                    "type": "string",
                    "description": "Type of roof material"
                },
                "foundation_type": {
                    "type": "string",
                    "description": "Type of foundation"
                },
                "additional_info": {
                    "type": "string",
                    "description": "Additional information about the property"
                }
            }
        },
        handler=UnderwritingMCPServer.submit_quote_for_underwriting
    ),
    
    Tool(
        name="get_quote_status",
        description="Get the current status and details of a submitted quote including decision, premium, and workflow state",
        inputSchema={
            "type": "object",
            "properties": {
                "quote_id": {
                    "type": "string",
                    "description": "Unique identifier for the quote"
                }
            }
        },
        handler=UnderwritingMCPServer.get_quote_status
    ),
    
    Tool(
        name="get_human_review_status",
        description="Get the human review status for a quote requiring manual underwriter review",
        inputSchema={
            "type": "object",
            "properties": {
                "quote_id": {
                    "type": "string",
                    "description": "Unique identifier for the quote"
                }
            }
        },
        handler=UnderwritingMCPServer.get_human_review_status
    )
]


async def main():
    """Main entry point for the MCP server."""
    
    # Create server instance
    server = Server("agentic-underwriting")
    
    # Register tools
    server.set_tools(TOOLS)
    
    # Add resources
    server.set_resources([
        Resource(
            uri="underwriting://guidelines",
            name="Underwriting Guidelines",
            description="Comprehensive underwriting guidelines and best practices",
            mimeType="text/plain"
        )
    ])
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                env="development"
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
