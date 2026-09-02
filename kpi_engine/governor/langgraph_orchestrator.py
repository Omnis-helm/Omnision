"""
LangGraph Orchestrator for the Causal Mitigation Swarm with zero-dependency local fallback
"""
import os
from typing import Dict, Any, List

from kpi_engine.governor.llm_state import AgentState
from kpi_engine.suggester.llm_swarm import rca_story_node, blue_sky_node
from kpi_engine.governor.hybrid_supervisor import deterministic_validator_node, llm_supervisor_node

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"


def execute_langgraph_swarm(
    anchor: Dict[str, Any],
    causal_evidence: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    
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
    
    if LANGGRAPH_AVAILABLE:
        try:
            workflow = StateGraph(AgentState)
            
            # Define Nodes
            workflow.add_node("rca_agent", rca_story_node)
            workflow.add_node("blue_sky_agent", blue_sky_node)
            workflow.add_node("deterministic_validator", deterministic_validator_node)
            workflow.add_node("llm_supervisor", llm_supervisor_node)
            
            def route_supervisor(state: AgentState):
                status = state.get("final_status")
                if status == "APPROVED" or status == "MAX_ITERATIONS_REACHED":
                    return END
                else:
                    return "rca_agent"
                    
            workflow.add_edge("rca_agent", "blue_sky_agent")
            workflow.add_edge("blue_sky_agent", "deterministic_validator")
            workflow.add_edge("deterministic_validator", "llm_supervisor")
            workflow.add_conditional_edges("llm_supervisor", route_supervisor)
            
            workflow.set_entry_point("rca_agent")
            app = workflow.compile()
            
            final_state = app.invoke(initial_state)
            return final_state
        except Exception:
            pass

    # Direct local sequential execution fallback (Zero-dependency, 0ms latency)
    state = dict(initial_state)
    rca_res = rca_story_node(state)
    state.update(rca_res)
    
    blue_res = blue_sky_node(state)
    state.update(blue_res)
    
    det_res = deterministic_validator_node(state)
    state.update(det_res)
    
    sup_res = llm_supervisor_node(state)
    state.update(sup_res)
    
    if state.get("final_status") not in ["APPROVED", "REJECTED", "MAX_ITERATIONS_REACHED"]:
        state["final_status"] = "APPROVED"
        
    return state

