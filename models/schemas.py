from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    ACCEPT = "ACCEPT"
    REFER = "REFER"
    DECLINE = "DECLINE"


class QuoteSubmission(BaseModel):
    applicant_name: str
    address: str
    property_type: str = Field(..., description="e.g., single_family, condo, commercial")
    coverage_amount: float = Field(..., gt=0)
    construction_year: Optional[int] = None
    square_footage: Optional[float] = None
    roof_type: Optional[str] = None
    foundation_type: Optional[str] = None
    additional_info: Optional[str] = None


class NormalizedAddress(BaseModel):
    street_address: str
    city: str
    state: str
    zip_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    county: Optional[str] = None


class HazardScores(BaseModel):
    wildfire_risk: float = Field(..., ge=0, le=1, description="0-1 scale")
    flood_risk: float = Field(..., ge=0, le=1, description="0-1 scale")
    wind_risk: float = Field(..., ge=0, le=1, description="0-1 scale")
    earthquake_risk: float = Field(..., ge=0, le=1, description="0-1 scale")


class PremiumBreakdown(BaseModel):
    base_premium: float
    hazard_surcharge: float
    total_premium: float
    rating_factors: Dict[str, float] = Field(default_factory=dict)


class EnrichmentResult(BaseModel):
    normalized_address: NormalizedAddress
    hazard_scores: HazardScores
    property_details: Dict[str, Any] = Field(default_factory=dict)


class RetrievalChunk(BaseModel):
    doc_id: str
    doc_version: str
    section: str
    chunk_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: Optional[float] = None


class UWTrigger(BaseModel):
    trigger_type: str  # e.g., "high_hazard", "missing_info", "guideline_violation"
    description: str
    severity: str  # e.g., "low", "medium", "high"
    requires_action: bool = False


class UWQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str  # e.g., "text", "choice", "numeric"
    required: bool = True
    options: Optional[List[str]] = None


class UWAssessment(BaseModel):
    eligibility_score: float = Field(..., ge=0, le=1)
    triggers: List[UWTrigger] = Field(default_factory=list)
    required_questions: List[UWQuestion] = Field(default_factory=list)
    reasoning: str
    citations: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class Decision(BaseModel):
    decision: DecisionType
    rationale: str
    citations: List[str] = Field(default_factory=list)
    premium: Optional[PremiumBreakdown] = None
    required_questions: List[UWQuestion] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat()
    })
    
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    timestamp: datetime
    execution_time_ms: Optional[int] = None


class WorkflowState(BaseModel):
    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat()
    })
    
    quote_submission: QuoteSubmission
    enrichment_result: Optional[EnrichmentResult] = None
    retrieved_guidelines: List[RetrievalChunk] = Field(default_factory=list)
    uw_assessment: Optional[UWAssessment] = None
    decision: Optional[Decision] = None
    premium_breakdown: Optional[PremiumBreakdown] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    current_node: Optional[str] = None
    missing_info: List[str] = Field(default_factory=list)
    additional_answers: Dict[str, Any] = Field(default_factory=dict)
    citation_guardrail_triggered: bool = False


class RunRecord(BaseModel):
    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat()
    })
    
    run_id: str
    created_at: datetime
    updated_at: datetime
    status: str  # e.g., "running", "completed", "failed", "waiting_for_info"
    workflow_state: WorkflowState
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
