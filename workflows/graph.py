from typing import Dict, Any
from langgraph.graph import StateGraph, END
from models.schemas import WorkflowState
from workflows.nodes import UnderwritingNodes


def create_underwriting_graph() -> StateGraph:
    """
    Create the LangGraph workflow for underwriting.
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
    workflow.add_node("rate", nodes.rate_policy)
    workflow.add_node("decide", nodes.make_decision)
    
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
            "missing_info": "decide",  # Skip to decision if missing info
            "enrich": "enrich"
        }
    )
    
    # Linear flow for successful validation
    workflow.add_edge("enrich", "retrieve_guidelines")
    workflow.add_edge("retrieve_guidelines", "uw_assess")
    workflow.add_edge("uw_assess", "rate")
    workflow.add_edge("rate", "decide")
    
    # End at decision
    workflow.add_edge("decide", END)
    
    return workflow


def run_underwriting_workflow(submission_data: Dict[str, Any]) -> WorkflowState:
    """
    Run the underwriting workflow with the given submission data.
    """
    # Create the graph
    graph = create_underwriting_graph()
    compiled_graph = graph.compile()
    
    # Create initial state
    from models.schemas import QuoteSubmission
    submission = QuoteSubmission(**submission_data)
    
    initial_state = WorkflowState(
        quote_submission=submission,
        current_node="start"
    )
    
    # Run the workflow
    result = compiled_graph.invoke(initial_state)
    
    return result
