import logging
from langgraph.graph import StateGraph, END
from backend.app.agents.state import AgentState
from backend.app.agents.nodes import (
    discover_process_node,
    generate_queries_node,
    execute_research_node,
    synthesize_evidence_node,
    design_transformation_node
)

logger = logging.getLogger(__name__)

# Build the LangGraph State Machine
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("discover_process", discover_process_node)
workflow.add_node("generate_queries", generate_queries_node)
workflow.add_node("execute_research", execute_research_node)
workflow.add_node("synthesize_evidence", synthesize_evidence_node)
workflow.add_node("design_transformation", design_transformation_node)

# Set Entry Point
workflow.set_entry_point("discover_process")

# Add Edges
workflow.add_edge("discover_process", "generate_queries")
workflow.add_edge("generate_queries", "execute_research")
workflow.add_edge("execute_research", "synthesize_evidence")
workflow.add_edge("synthesize_evidence", "design_transformation")
workflow.add_edge("design_transformation", END)

# Compile the Workflow
app_graph = workflow.compile()

async def run_transformation_workflow(
    process_id: str, 
    industry: str, 
    process_name: str, 
    search_provider: str
) -> dict:
    """
    Executes the multi-agent transformation workflow in LangGraph.
    """
    logger.info(f"Triggering LangGraph workflow for process ID: {process_id}")
    
    initial_state = {
        "process_id": process_id,
        "industry": industry,
        "process_name": process_name,
        "search_provider": search_provider,
        "current_activities": [],
        "research_queries": [],
        "search_results": [],
        "evidence_analyses": [],
        "ai_opportunities": [],
        "future_activities": [],
        "error": ""
    }
    
    try:
        final_state = await app_graph.ainvoke(initial_state)
        return final_state
    except Exception as e:
        logger.error(f"Failed executing LangGraph workflow: {e}")
        return {**initial_state, "error": f"LangGraph execution exception: {e}"}
