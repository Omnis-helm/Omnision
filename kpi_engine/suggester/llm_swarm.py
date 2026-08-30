"""
LangGraph Swarm Nodes - Multi-Agent Generator
"""
import os
import json
from typing import Dict, Any, List
from kpi_engine.governor.llm_factory import get_llm
from kpi_engine.config import CONFIG
from kpi_engine.governor.llm_state import AgentState
import hashlib

def _generate_proposal(state: AgentState, llm_provider: str, persona: str, layer: str, temp: float) -> Dict[str, Any]:
    llm = get_llm(provider=llm_provider, temperature=temp)
    anchor = state.get("anchor_context", {})
    evidence = state.get("causal_evidence", [])
    feedback = state.get("supervisor_feedback", "")
    
    prompt = (
        f"You are the {persona}.\n"
        f"KPI Impacted: {anchor.get('metric_name', 'Unknown')}\n"
        f"Primary Driver: {evidence[0].get('content', 'Unknown') if evidence else 'Unknown'}\n"
        f"Generate a robust operational JSON solution.\n"
        f"Required keys: action, source_layer, estimated_cost_usd, time_to_impact_minutes, raci_owner, approval_status.\n"
    )
    if feedback:
        prompt += f"\nPrevious Supervisor Feedback: {feedback}\nAddress this feedback in your new solution."
        
    response = llm.invoke(prompt)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        proposal = json.loads(content)
        
        action_hash = hashlib.md5(proposal.get("action", "fallback").encode()).hexdigest()[:8].upper()
        proposal["action_id"] = f"ACT-{action_hash}"
        proposal["source_layer"] = layer
        if "critic_verdict" not in proposal:
            proposal["critic_verdict"] = "PENDING_SUPERVISOR"
            
    except Exception as e:
        err_hash = hashlib.md5(str(e).encode()).hexdigest()[:8].upper()
        proposal = {
            "action_id": f"ACT-ERR-{err_hash}",
            "action": f"Fallback: Error parsing LLM JSON ({llm_provider})",
            "source_layer": layer,
            "estimated_cost_usd": 0.0,
            "time_to_impact_minutes": 0,
            "raci_owner": "SYSTEM",
            "approval_status": "ERROR",
            "critic_verdict": f"JSON Parsing Error: {str(e)}"
        }
    return proposal

def rca_story_node(state: AgentState) -> Dict[str, Any]:
    """Generates the primary prescriptive RCA."""
    provider = state.get("primary_llm_provider", "mock")
    proposal = _generate_proposal(state, provider, "Omnision Prescriptive Swarm", "Layer 3 - Prescriptive Swarm", 0.4)
    
    proposals = state.get("proposals", [])
    proposals.append(proposal)
    
    return {
        "proposals": proposals,
        "tokens_consumed": state.get("tokens_consumed", 0) + 500
    }

def blue_sky_node(state: AgentState) -> Dict[str, Any]:
    """Generates unconventional, highly creative alternative ideas (Shadow Run)."""
    provider = state.get("bluesky_llm_provider", "mock")
    # Only run Blue-Sky on first iteration to save tokens
    if state.get("iteration_count", 0) > 0:
        return {}
        
    proposal = _generate_proposal(state, provider, "Blue-Sky Challenger (Creative, Unconstrained)", "Layer 5 - Blue-Sky", 0.9)
    # Flag it for shadow run
    proposal["requires_shadow_run"] = True
    
    proposals = state.get("proposals", [])
    proposals.append(proposal)
    
    return {
        "proposals": proposals,
        "tokens_consumed": state.get("tokens_consumed", 0) + 500
    }
