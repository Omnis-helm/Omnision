"""
LangGraph Orchestrator connecting Swarm and Supervisor
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from kpi_engine.governor.llm_state import AgentState
from kpi_engine.suggester.llm_swarm import swarm_agent_node
from kpi_engine.governor.hybrid_supervisor import deterministic_validator_node, llm_supervisor_node

def route_supervisor_decision(state: AgentState) -> str:
    """Conditional routing based on Supervisor's decision."""
    status = state.get("final_status")
    if status == "APPROVED":
        return END
    elif status == "MAX_ITERATIONS_REACHED":
        return END
    else:
        # REJECTED or anything else goes back to the swarm
        return "swarm_agent"

from kpi_engine.governor.external_tools import WebIntelligenceTools

def web_intelligence_node(state: AgentState) -> Dict[str, Any]:
    """Uses external tools to gather macro context before the swarm generates proposals."""
    evidence = state.get("causal_evidence", [])
    
    # Simple heuristic: If there is no highly causal internal evidence, check external
    if not any(e.get("causal_impact", 0) > 0.80 for e in evidence):
        tools = WebIntelligenceTools()
        
        # Hardcoding a simulated news headline for demonstration
        news = "Competitor RivalRetail launched a massive flash sale slashing prices by 20%."
        external_context = tools.run_external_evaluation(news_headline=news, ticker="WMT")
        
        # Update context
        new_context = dict(state.get("context", {}))
        new_context["external_web_intelligence"] = external_context
        return {"context": new_context, "tokens_consumed": state.get("tokens_consumed", 0) + 150}
    
    return {}

def build_swarm_graph():
    """Builds and compiles the LangGraph."""
    workflow = StateGraph(AgentState)
    
    # 1. Add Nodes
    workflow.add_node("web_intelligence", web_intelligence_node)
    workflow.add_node("swarm_agent", swarm_agent_node)
    workflow.add_node("validator", deterministic_validator_node)
    workflow.add_node("llm_supervisor", llm_supervisor_node)
    
    # 2. Define standard edges
    workflow.set_entry_point("web_intelligence")
    workflow.add_edge("web_intelligence", "swarm_agent")
    workflow.add_edge("swarm_agent", "validator")
    workflow.add_edge("validator", "llm_supervisor")
    
    # 3. Define conditional edges (The iterative loop)
    workflow.add_conditional_edges(
        "llm_supervisor",
        route_supervisor_decision,
        {
            END: END,
            "swarm_agent": "swarm_agent"
        }
    )
    
    return workflow.compile()

# Global compiled graph singleton
langgraph_swarm = build_swarm_graph()

def execute_langgraph_swarm(
    anchor: Dict[str, Any],
    causal_evidence: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Helper to kick off the graph and format the output."""
    initial_state = {
        "anchor_context": anchor,
        "causal_evidence": causal_evidence,
        "context": context,
        "proposals": [],
        "supervisor_feedback": "",
        "iteration_count": 0,
        "final_status": "PENDING",
        "tokens_consumed": 0
    }
    
    final_state = langgraph_swarm.invoke(initial_state)
    return final_state
