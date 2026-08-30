"""
LangGraph Swarm Nodes - Multi-Agent Generator
"""
import os
import json
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from kpi_engine.config import CONFIG
from kpi_engine.governor.llm_state import AgentState
import uuid

class MockLLM:
    """Fallback mock LLM to ensure demo runs without API keys."""
    def invoke(self, prompt: str) -> AIMessage:
        return AIMessage(content=json.dumps({
            "action": "Implement Phased Mitigation Protocol via LangGraph Swarm",
            "source_layer": "Layer 3 - Prescriptive Swarm",
            "estimated_cost_usd": 1500.0,
            "time_to_impact_minutes": 30,
            "raci_owner": "Platform Engineering",
            "approval_status": "PENDING_REVIEW"
        }))

def get_swarm_llm():
    api_key = os.getenv("OPENAI_API_KEY", CONFIG.openai_api_key)
    if api_key and api_key != "your_openai_api_key_here":
        return ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.8)
    return MockLLM()

def swarm_agent_node(state: AgentState) -> Dict[str, Any]:
    """The unified Swarm Agent that generates candidate solutions."""
    llm = get_swarm_llm()
    
    # Build prompt context
    anchor = state.get("anchor_context", {})
    evidence = state.get("causal_evidence", [])
    feedback = state.get("supervisor_feedback", "")
    
    prompt = (
        f"You are the Omnision Prescriptive Swarm.\n"
        f"KPI Impacted: {anchor.get('metric_name', 'Unknown')}\n"
        f"Primary Driver: {evidence[0].get('content', 'Unknown') if evidence else 'Unknown'}\n"
        f"Generate a robust operational JSON solution.\n"
        f"Required keys: action, source_layer, estimated_cost_usd, time_to_impact_minutes, raci_owner, approval_status.\n"
    )
    if feedback:
        prompt += f"\nPrevious Supervisor Feedback: {feedback}\nAddress this feedback in your new solution."
        
    response = llm.invoke(prompt)
    
    # Parse output
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        proposal = json.loads(content)
        
        import hashlib
        action_hash = hashlib.md5(proposal.get("action", "fallback").encode()).hexdigest()[:8].upper()
        proposal["action_id"] = f"ACT-SWARM-{action_hash}"
        if "critic_verdict" not in proposal:
            proposal["critic_verdict"] = "PENDING_SUPERVISOR"
            
    except Exception as e:
        import hashlib
        err_hash = hashlib.md5(str(e).encode()).hexdigest()[:8].upper()
        proposal = {
            "action_id": f"ACT-ERR-{err_hash}",
            "action": "Fallback: Error parsing LLM JSON",
            "source_layer": "Error Handling",
            "estimated_cost_usd": 0.0,
            "time_to_impact_minutes": 0,
            "raci_owner": "System",
            "approval_status": "REJECTED",
            "error_msg": str(e),
            "raw_output": response.content
        }
        
    # Append the proposal to state
    current_proposals = list(state.get("proposals", []))
    current_proposals.append(proposal)
    
    # Update iteration count
    iterations = state.get("iteration_count", 0) + 1
    
    # Approx token cost simulation
    tokens = state.get("tokens_consumed", 0) + 300
    
    return {
        "proposals": current_proposals,
        "iteration_count": iterations,
        "tokens_consumed": tokens
    }
