from typing import Dict, Any
from langgraph.graph import StateGraph, END
from models.schemas import WorkflowState, DecisionType
from workflows.nodes import UnderwritingNodes


def create_agentic_underwriting_graph() -> StateGraph:
    """
    Create the enhanced LangGraph workflow with missing-info loop.
    """
    # Initialize nodes
    nodes = UnderwritingNodes()
    
    # Create the graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("validate", nodes.validate_submission)
    workflow.add_node("enrich", nodes.enrich_data)
    workflow.add_node("retrieve_guidelines", nodes.retrieve_guidelines)
    workflow.add_node("uw_assess", nodes.assess_underwriting)
    workflow.add_node("citation_guardrail", nodes.apply_citation_guardrail)
    workflow.add_node("rate", nodes.rate_policy)
    workflow.add_node("decide", nodes.make_decision)
    workflow.add_node("handle_missing_info", nodes.handle_missing_info)
    
    # Define the flow
    workflow.set_entry_point("validate")
    
    # Check if validation passes
    def should_continue(state: WorkflowState) -> str:
        if state.missing_info:
            return "missing_info"
        return "enrich"
    
    workflow.add_conditional_edges(
        "validate",
        should_continue,
        {
            "missing_info": "handle_missing_info",
            "enrich": "enrich"
        }
    )
    
    # Handle missing info - check if questions were answered
    def check_missing_info_resolved(state: WorkflowState) -> str:
        # Check if all missing info has been addressed
        if state.missing_info:
            return "still_missing"
        return "resolved"
    
    workflow.add_conditional_edges(
        "handle_missing_info",
        check_missing_info_resolved,
        {
            "still_missing": "decide",  # Still missing info -> refer for manual review
            "resolved": "enrich"  # Info provided -> continue processing
        }
    )
    
    # Linear flow for successful validation
    workflow.add_edge("enrich", "retrieve_guidelines")
    workflow.add_edge("retrieve_guidelines", "uw_assess")
    workflow.add_edge("uw_assess", "citation_guardrail")
    
    # Check if citation guardrail was triggered
    def check_citation_guardrail(state: WorkflowState) -> str:
        if hasattr(state, 'citation_guardrail_triggered') and state.citation_guardrail_triggered:
            return "guardrail_triggered"
        return "guardrail_passed"
    
    workflow.add_conditional_edges(
        "citation_guardrail",
        check_citation_guardrail,
        {
            "guardrail_triggered": "decide",  # Skip rating, go straight to decision
            "guardrail_passed": "rate"
        }
    )
    
    workflow.add_edge("rate", "decide")
    
    # Check if decision requires more information
    def check_decision_loop(state: WorkflowState) -> str:
        if (state.decision and 
            state.decision.decision == DecisionType.REFER and 
            state.decision.required_questions):
            return "needs_questions"
        return "final"
    
    workflow.add_conditional_edges(
        "decide",
        check_decision_loop,
        {
            "needs_questions": "handle_missing_info",
            "final": END
        }
    )
    
    return workflow


def run_agentic_underwriting_workflow(submission_data: Dict[str, Any], 
                                    additional_answers: Dict[str, Any] = None) -> WorkflowState:
    """
    Run the agentic underwriting workflow with the given submission data.
    """
    # Create the graph
    graph = create_agentic_underwriting_graph()
    compiled_graph = graph.compile()
    
    # Create initial state
    from models.schemas import QuoteSubmission
    submission = QuoteSubmission(**submission_data)
    
    initial_state = WorkflowState(
        quote_submission=submission,
        current_node="start",
        additional_answers=additional_answers or {}
    )
    
    # Run the workflow
    result = compiled_graph.invoke(initial_state)
    
    return result
