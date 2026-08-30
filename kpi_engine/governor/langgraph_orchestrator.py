"""
LangGraph Orchestrator for the Causal Mitigation Swarm
"""
import os
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from kpi_engine.governor.llm_state import AgentState
from kpi_engine.suggester.llm_swarm import rca_story_node, blue_sky_node
from kpi_engine.governor.hybrid_supervisor import deterministic_validator_node, llm_supervisor_node

def execute_langgraph_swarm(
    anchor: Dict[str, Any],
    causal_evidence: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    workflow.add_node("rca_agent", rca_story_node)
    workflow.add_node("blue_sky_agent", blue_sky_node)
    workflow.add_node("deterministic_validator", deterministic_validator_node)
    workflow.add_node("llm_supervisor", llm_supervisor_node)
    
    # Routing function based on feedback
    def route_supervisor(state: AgentState):
        status = state.get("final_status")
        if status == "APPROVED" or status == "MAX_ITERATIONS_REACHED":
            return END
        else:
            return "rca_agent" # Loop back to primary agent for fixes
            
    # Define Edges (Linear for now: RCA -> BlueSky -> Validator -> Supervisor -> End/Loop)
    workflow.add_edge("rca_agent", "blue_sky_agent")
    workflow.add_edge("blue_sky_agent", "deterministic_validator")
    workflow.add_edge("deterministic_validator", "llm_supervisor")
    workflow.add_conditional_edges("llm_supervisor", route_supervisor)
    
    workflow.set_entry_point("rca_agent")
    app = workflow.compile()
    
    primary_llm = context.get("primary_llm_provider", "mock")
    bluesky_llm = context.get("bluesky_llm_provider", "mock")
    
    initial_state = {
        "anchor_context": anchor,
        "causal_evidence": causal_evidence,
        "context": context,
        "primary_llm_provider": primary_llm,
        "bluesky_llm_provider": bluesky_llm,
        "proposals": [],
        "supervisor_feedback": None,
        "iteration_count": 0,
        "final_status": "PENDING",
        "tokens_consumed": 0
    }
    
    final_state = app.invoke(initial_state)
    return final_state
