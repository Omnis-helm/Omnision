"""
Hybrid Neuro-Symbolic Supervisor
"""
import os
import json
import random
from typing import Dict, Any
from kpi_engine.governor.llm_factory import get_llm
from kpi_engine.config import CONFIG
from kpi_engine.governor.llm_state import AgentState

def check_liveness_ping(action: str) -> bool:
    """Simulates a real-time network ping to an operational lever (e.g. AWS API, LaunchDarkly)."""
    # For demo purposes, we randomly simulate a stale lever 10% of the time, 
    # unless it explicitly says 'AWS' which we assume is up.
    if "AWS" in action:
        return True
    return random.random() > 0.10


def deterministic_validator_node(state: AgentState) -> Dict[str, Any]:
    """Layer 1: Hardcoded rules and schema checks."""
    proposals = state.get("proposals", [])
    if not proposals:
        return {"final_status": "REJECTED", "supervisor_feedback": "No proposals generated."}
        
    latest_proposal = proposals[-1]
    iterations = state.get("iteration_count", 0)
    
    # 1. Max Iterations Check
    max_iters = CONFIG.swarm_max_iterations
    if iterations >= max_iters:
        return {"final_status": "MAX_ITERATIONS_REACHED", "supervisor_feedback": f"Max iterations ({max_iters}) reached."}
        
    # 2. Schema Check
    required_keys = ["action", "estimated_cost_usd", "raci_owner"]
    for key in required_keys:
        if key not in latest_proposal:
            return {"final_status": "REJECTED", "supervisor_feedback": f"Invalid JSON Schema: Missing '{key}'"}
            
    # 3. Security / Forbidden Action Check (Simulated PII/Destructive actions)
    action_str = latest_proposal.get("action", "").lower()
    forbidden_terms = ["delete database", "drop table", "shutdown server", "ssn"]
    for term in forbidden_terms:
        if term in action_str:
            return {"final_status": "REJECTED", "supervisor_feedback": f"Security Violation: '{term}' is strictly forbidden."}

    # 3.5 Stale Lever Liveness Check
    if not check_liveness_ping(action_str):
        return {"final_status": "REJECTED", "supervisor_feedback": "Technical lever failed liveness ping. The operational endpoint is currently unresponsive."}
            
    # 4. Financial Budget Check (Neuro-symbolic bounds)
    cost = float(latest_proposal.get("estimated_cost_usd", 0.0))
    if cost > CONFIG.vp_approval_required_cost_usd:
        # Only reject if we don't have logic handling VP approval, but let's just reject for demo bounds
        return {"final_status": "REJECTED", "supervisor_feedback": f"Cost exceeds ultimate bounds (${CONFIG.vp_approval_required_cost_usd})."}
        
    # Passed all deterministic checks, route to LLM Supervisor
    return {"final_status": "PENDING_LLM_REVIEW", "supervisor_feedback": "Passed deterministic validation."}

from kpi_engine.ml.local_ml_engine import LocalSemanticSupervisor

def llm_supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Layer 2: LLM or Local Semantic Supervisor logically reviews the proposal."""
    status = state.get("final_status")
    if status != "PENDING_LLM_REVIEW":
        return {} # Don't overwrite if rejected by deterministic layer
        
    proposals = state.get("proposals", [])
    latest_proposal = proposals[-1]
    evidence = state.get("causal_evidence", [])
    primary_cause = evidence[0].get("content", "Unknown") if evidence else "Unknown"
    proposed_action = latest_proposal.get("action", "")

    provider = state.get("primary_llm_provider", "mock")

    # Fast Local/Mock Semantic Alignment Check
    if provider in ["mock", "local"] or getattr(CONFIG, "prefer_local_tools", True):
        decision, reason, _ = LocalSemanticSupervisor.evaluate_alignment(primary_cause, proposed_action)
        return {
            "final_status": decision,
            "supervisor_feedback": reason,
            "tokens_consumed": state.get("tokens_consumed", 0)
        }
    
    llm = get_llm(provider=provider, temperature=0.0)
    
    prompt = (
        f"You are the Omnision Chief Supervisor.\n"
        f"Review this proposed action for logical alignment with the Causal Root Cause.\n"
        f"Primary Cause: {primary_cause}\n"
        f"Proposed Action: {proposed_action}\n\n"
        f"You MUST respond ONLY in strictly valid JSON with exactly these two keys:\n"
        f'  "decision": "APPROVED" or "REJECTED"\n'
        f'  "reason": "String explaining why"\n'
        f"Do NOT include markdown backticks or any other text.\n"
    )
    
    response = llm.invoke(prompt)
    
    try:
        content = str(response.content).strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        result = json.loads(content)
        decision = result.get("decision", "REJECTED")
        reason = result.get("reason", "No reason provided by LLM.")
    except Exception as e:
        decision = "REJECTED"
        reason = f"Supervisor parsing error: {str(e)}"
        
    tokens = state.get("tokens_consumed", 0) + 150
        
    return {
        "final_status": decision,
        "supervisor_feedback": reason,
        "tokens_consumed": tokens
    }





