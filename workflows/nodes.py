from typing import Dict, Any, List
from datetime import datetime
import uuid
from langgraph.graph import StateGraph, END
from models.schemas import (
    WorkflowState, QuoteSubmission, EnrichmentResult, 
    UWAssessment, Decision, DecisionType, UWTrigger, UWQuestion,
    ToolCall, RetrievalChunk
)
from tools import AddressNormalizeTool, HazardScoreTool, RatingTool
from app.rag_engine import RAGEngine


class UnderwritingNodes:
    """
    Collection of LangGraph nodes for the underwriting workflow.
    """
    
    def __init__(self):
        self.address_tool = AddressNormalizeTool()
        self.hazard_tool = HazardScoreTool()
        self.rating_tool = RatingTool()
        self.rag_engine = RAGEngine()
        
        # Initialize RAG with documents
        self.rag_engine.ingest_documents()
    
    def validate_submission(self, state) -> dict:
        """
        Validate the quote submission for completeness and basic requirements.
        """
        # Handle both dict and WorkflowState inputs
        if isinstance(state, dict):
            from models.schemas import QuoteSubmission
            submission = QuoteSubmission(**state['quote_submission'])
        else:
            submission = state.quote_submission
            
        missing_info = []
        
        # Check required fields
        if not submission.applicant_name.strip():
            missing_info.append("applicant_name")
        
        if not submission.address.strip():
            missing_info.append("address")
        
        if not submission.property_type.strip():
            missing_info.append("property_type")
        
        if submission.coverage_amount <= 0:
            missing_info.append("valid coverage_amount")
        
        # Check for reasonable values
        if submission.coverage_amount > 10000000:  # $10M limit
            missing_info.append("coverage_amount exceeds maximum limit")
        
        if submission.construction_year and submission.construction_year > 2024:
            missing_info.append("construction_year cannot be in the future")
        
        if submission.construction_year and submission.construction_year < 1800:
            missing_info.append("construction_year seems too old")
        
        # Log tool call
        tool_call = ToolCall(
            tool_name="validate_submission",
            input_data={"submission": submission.model_dump()},
            output_data={"missing_info": missing_info, "valid": len(missing_info) == 0},
            timestamp=datetime.now()
        )
        
        # Return updated state as dict
        if isinstance(state, dict):
            state['missing_info'] = missing_info
            state['current_node'] = "validate"
            if 'tool_calls' not in state:
                state['tool_calls'] = []
            state['tool_calls'].append(tool_call)
        else:
            state.missing_info = missing_info
            state.current_node = "validate"
            state.tool_calls.append(tool_call)
        
        return state
    
    def enrich_data(self, state: WorkflowState) -> WorkflowState:
        """
        Enrich the submission with normalized address and hazard scores.
        """
        submission = state.quote_submission
        
        # Normalize address
        address_result = self.address_tool(submission)
        normalized_address = address_result["normalized_address"]
        
        # Calculate hazard scores
        from models.schemas import NormalizedAddress
        addr = NormalizedAddress(**normalized_address)
        hazard_result = self.hazard_tool(addr)
        hazard_scores = hazard_result["hazard_scores"]
        
        # Create enrichment result
        from models.schemas import HazardScores
        enrichment = EnrichmentResult(
            normalized_address=addr,
            hazard_scores=HazardScores(**hazard_scores),
            property_details={
                "property_type": submission.property_type,
                "construction_year": submission.construction_year,
                "square_footage": submission.square_footage,
                "roof_type": submission.roof_type,
                "foundation_type": submission.foundation_type
            }
        )
        
        state.enrichment_result = enrichment
        state.current_node = "enrich"
        
        # Log tool calls
        address_call = ToolCall(
            tool_name="address_normalize",
            input_data={"address": submission.address},
            output_data=address_result,
            timestamp=datetime.now()
        )
        
        hazard_call = ToolCall(
            tool_name="hazard_score",
            input_data={"address": normalized_address},
            output_data=hazard_result,
            timestamp=datetime.now()
        )
        
        state.tool_calls.extend([address_call, hazard_call])
        
        return state
    
    def retrieve_guidelines(self, state: WorkflowState) -> WorkflowState:
        """
        Retrieve relevant underwriting guidelines based on the submission.
        """
        submission = state.quote_submission
        enrichment = state.enrichment_result
        
        # Build search query based on submission characteristics
        query_parts = []
        
        # Property type
        query_parts.append(f"property type {submission.property_type}")
        
        # Hazard risks
        if enrichment:
            if enrichment.hazard_scores.wildfire_risk > 0.5:
                query_parts.append("wildfire risk assessment")
            if enrichment.hazard_scores.flood_risk > 0.5:
                query_parts.append("flood risk evaluation")
            if enrichment.hazard_scores.wind_risk > 0.5:
                query_parts.append("wind damage risk")
            if enrichment.hazard_scores.earthquake_risk > 0.5:
                query_parts.append("earthquake hazard")
        
        # Construction details
        if submission.construction_year:
            if submission.construction_year < 1940:
                query_parts.append("old construction requirements")
            elif submission.construction_year < 1970:
                query_parts.append("older building standards")
        
        if submission.roof_type:
            query_parts.append(f"roof {submission.roof_type}")
        
        if submission.foundation_type:
            query_parts.append(f"foundation {submission.foundation_type}")
        
        # Combine into query
        query = " ".join(query_parts)
        
        # Retrieve guidelines
        retrieved_chunks = self.rag_engine.retrieve(query, n_results=5)
        
        state.retrieved_guidelines = retrieved_chunks
        state.current_node = "retrieve_guidelines"
        
        # Log tool call
        tool_call = ToolCall(
            tool_name="rag_retrieval",
            input_data={"query": query, "n_results": 5},
            output_data={"retrieved_chunks": [chunk.model_dump() for chunk in retrieved_chunks]},
            timestamp=datetime.now()
        )
        state.tool_calls.append(tool_call)
        
        return state
    
    def assess_underwriting(self, state: WorkflowState) -> WorkflowState:
        """
        Perform underwriting assessment based on enriched data and guidelines.
        """
        submission = state.quote_submission
        enrichment = state.enrichment_result
        guidelines = state.retrieved_guidelines
        
        # Initialize assessment
        triggers = []
        required_questions = []
        citations = []
        eligibility_score = 0.8  # Start with neutral score
        
        # Check property eligibility
        if submission.property_type not in ["single_family", "condo", "townhouse"]:
            triggers.append(UWTrigger(
                trigger_type="property_type",
                description=f"Property type {submission.property_type} may not be eligible",
                severity="high",
                requires_action=True
            ))
            eligibility_score -= 0.3
        
        # Check construction year
        if submission.construction_year:
            if submission.construction_year < 1940:
                triggers.append(UWTrigger(
                    trigger_type="construction_age",
                    description="Property constructed before 1940 requires additional review",
                    severity="medium",
                    requires_action=True
                ))
                eligibility_score -= 0.2
                required_questions.append(UWQuestion(
                    question_id="construction_updates",
                    question_text="What updates have been made to electrical, plumbing, and roofing systems?",
                    question_type="text",
                    required=True
                ))
        
        # Check hazard scores
        if enrichment:
            if enrichment.hazard_scores.wildfire_risk > 0.7:
                triggers.append(UWTrigger(
                    trigger_type="wildfire_risk",
                    description="High wildfire risk detected",
                    severity="high",
                    requires_action=True
                ))
                eligibility_score -= 0.3
                required_questions.append(UWQuestion(
                    question_id="wildfire_mitigation",
                    question_text="What wildfire mitigation measures are in place?",
                    question_type="text",
                    required=True
                ))
            elif enrichment.hazard_scores.wildfire_risk > 0.5:
                triggers.append(UWTrigger(
                    trigger_type="wildfire_risk",
                    description="Moderate wildfire risk detected",
                    severity="medium",
                    requires_action=False
                ))
                eligibility_score -= 0.1
            
            if enrichment.hazard_scores.flood_risk > 0.7:
                triggers.append(UWTrigger(
                    trigger_type="flood_risk",
                    description="High flood risk detected",
                    severity="high",
                    requires_action=True
                ))
                eligibility_score -= 0.3
                required_questions.append(UWQuestion(
                    question_id="elevation_certificate",
                    question_text="Is an elevation certificate available?",
                    question_type="choice",
                    required=True,
                    options=["Yes", "No", "Unknown"]
                ))
        
        # Add citations from retrieved guidelines
        for chunk in guidelines:
            if any(keyword in chunk.text.lower() for keyword in ["risk", "requirement", "eligible", "standard"]):
                citations.append(f"{chunk.doc_id}:{chunk.section}")
        
        # Ensure eligibility score is within bounds
        eligibility_score = max(0, min(1, eligibility_score))
        
        # Generate reasoning
        reasoning_parts = []
        if triggers:
            reasoning_parts.append(f"Identified {len(triggers)} risk factors:")
            for trigger in triggers:
                reasoning_parts.append(f"- {trigger.description}")
        
        if not triggers:
            reasoning_parts.append("No significant risk factors identified")
        
        reasoning_parts.append(f"Eligibility score: {eligibility_score:.2f}")
        
        # Create assessment
        assessment = UWAssessment(
            eligibility_score=eligibility_score,
            triggers=triggers,
            required_questions=required_questions,
            reasoning="; ".join(reasoning_parts),
            citations=citations,
            confidence=0.85 if len(citations) > 0 else 0.6
        )
        
        state.uw_assessment = assessment
        state.current_node = "uw_assess"
        
        # Log tool call
        tool_call = ToolCall(
            tool_name="underwriting_assessment",
            input_data={
                "submission": submission.model_dump(),
                "enrichment": enrichment.model_dump() if enrichment else {},
                "guidelines_count": len(guidelines)
            },
            output_data={"assessment": assessment.model_dump()},
            timestamp=datetime.now()
        )
        state.tool_calls.append(tool_call)
        
        return state
    
    def apply_citation_guardrail(self, state: WorkflowState) -> WorkflowState:
        """
        Apply strict citation guardrail - force REFER if assessment lacks citations.
        """
        assessment = state.uw_assessment
        
        if not assessment or not assessment.citations:
            # Force REFER due to insufficient evidence
            from models.schemas import Decision
            decision = Decision(
                decision=DecisionType.REFER,
                rationale="Insufficient evidence: Underwriting assessment lacks proper citations from guidelines",
                citations=[],
                next_steps=["Manual underwriter review required", "Guideline citations needed for decision"]
            )
            
            state.decision = decision
            state.citation_guardrail_triggered = True
            
            # Log guardrail activation
            tool_call = ToolCall(
                tool_name="citation_guardrail",
                input_data={"assessment_citations": assessment.citations if assessment else []},
                output_data={"guardrail_triggered": True, "forced_decision": decision.model_dump()},
                timestamp=datetime.now()
            )
            state.tool_calls.append(tool_call)
        else:
            state.citation_guardrail_triggered = False
        
        state.current_node = "citation_guardrail"
        return state
    
    def rate_policy(self, state: WorkflowState) -> WorkflowState:
        """
        Calculate premium based on risk assessment.
        """
        submission = state.quote_submission
        enrichment = state.enrichment_result
        
        # Prepare rating data
        rating_data = {
            "coverage_amount": submission.coverage_amount,
            "property_type": submission.property_type,
            "hazard_scores": enrichment.hazard_scores.model_dump() if enrichment else {},
            "construction_year": submission.construction_year
        }
        
        # Calculate premium
        rating_result = self.rating_tool(rating_data)
        premium_breakdown = rating_result["premium_breakdown"]
        
        # Store premium in state for decision making
        state.premium_breakdown = premium_breakdown
        state.current_node = "rate"
        
        # Log tool call
        tool_call = ToolCall(
            tool_name="rating_calculation",
            input_data=rating_data,
            output_data=rating_result,
            timestamp=datetime.now()
        )
        state.tool_calls.append(tool_call)
        
        return state
    
    def handle_missing_info(self, state: WorkflowState) -> WorkflowState:
        """
        Handle missing information by processing additional answers or generating questions.
        """
        # Process additional answers if provided
        if state.additional_answers:
            # Update submission with additional answers
            submission_dict = state.quote_submission.model_dump()
            
            for field, value in state.additional_answers.items():
                if hasattr(state.quote_submission, field):
                    setattr(state.quote_submission, field, value)
            
            # Clear missing info after processing answers
            state.missing_info = []
            
            # Log the update
            tool_call = ToolCall(
                tool_name="process_additional_answers",
                input_data={"additional_answers": state.additional_answers},
                output_data={"updated_submission": state.quote_submission.model_dump()},
                timestamp=datetime.now()
            )
            state.tool_calls.append(tool_call)
            
        else:
            # Generate questions for missing information
            missing_questions = []
            for missing_field in state.missing_info:
                question = UWQuestion(
                    question_id=f"missing_{missing_field}",
                    question_text=f"Please provide {missing_field.replace('_', ' ')}",
                    question_type="text",
                    required=True
                )
                missing_questions.append(question)
            
            # Create a referral decision for missing info
            from models.schemas import Decision
            decision = Decision(
                decision=DecisionType.REFER,
                rationale=f"Additional information required: {', '.join(state.missing_info)}",
                citations=[],
                required_questions=missing_questions,
                next_steps=["Provide missing information and resubmit"]
            )
            
            state.decision = decision
            
            # Log the question generation
            tool_call = ToolCall(
                tool_name="generate_missing_info_questions",
                input_data={"missing_info": state.missing_info},
                output_data={"questions": [q.model_dump() for q in missing_questions]},
                timestamp=datetime.now()
            )
            state.tool_calls.append(tool_call)
        
        state.current_node = "handle_missing_info"
        return state
    
    def make_decision(self, state: WorkflowState) -> WorkflowState:
        """
        Make final underwriting decision based on assessment.
        """
        assessment = state.uw_assessment
        missing_info = state.missing_info
        
        # Check if we need more information
        if missing_info:
            decision = Decision(
                decision=DecisionType.REFER,
                rationale=f"Missing required information: {', '.join(missing_info)}",
                citations=[],
                required_questions=[
                    UWQuestion(
                        question_id=f"missing_{field}",
                        question_text=f"Please provide {field.replace('_', ' ')}",
                        question_type="text",
                        required=True
                    ) for field in missing_info
                ],
                next_steps=["Provide missing information and resubmit"]
            )
        elif assessment.eligibility_score >= 0.7 and not any(t.severity == "high" for t in assessment.triggers):
            decision = Decision(
                decision=DecisionType.ACCEPT,
                rationale=f"Property meets eligibility criteria. Score: {assessment.eligibility_score:.2f}",
                citations=assessment.citations,
                premium=state.premium_breakdown,
                next_steps=["Policy issuance", "Payment collection", "Policy document delivery"]
            )
        elif assessment.eligibility_score < 0.5 or any(t.severity == "high" for t in assessment.triggers):
            decision = Decision(
                decision=DecisionType.DECLINE,
                rationale=f"Property does not meet eligibility requirements. Score: {assessment.eligibility_score:.2f}",
                citations=assessment.citations,
                next_steps=["Notify applicant of decline", "Provide specific reasons", "Suggest improvements for future consideration"]
            )
        else:
            decision = Decision(
                decision=DecisionType.REFER,
                rationale=f"Property requires manual review. Score: {assessment.eligibility_score:.2f}",
                citations=assessment.citations,
                required_questions=assessment.required_questions,
                next_steps=["Underwriter manual review", "Additional documentation may be required"]
            )
        
        state.decision = decision
        state.current_node = "decide"
        
        # Log tool call
        tool_call = ToolCall(
            tool_name="decision_making",
            input_data={
                "eligibility_score": assessment.eligibility_score,
                "triggers": [t.model_dump() for t in assessment.triggers],
                "missing_info": missing_info
            },
            output_data={"decision": decision.model_dump()},
            timestamp=datetime.now()
        )
        state.tool_calls.append(tool_call)
        
        return state
