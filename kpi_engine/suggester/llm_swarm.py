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

from kpi_engine.ml.local_ml_engine import LLMResponseCache

def _generate_proposal(state: AgentState, llm_provider: str, persona: str, layer: str, temp: float) -> Dict[str, Any]:
    anchor = state.get("anchor_context", {})
    evidence = state.get("causal_evidence", [])
    feedback = state.get("supervisor_feedback", "")
    
    anchor_metric = anchor.get("metric_name", "Unknown")
    primary_driver = evidence[0].get("content", "Unknown") if evidence else "Unknown"

    # Check Cache first if LLM Caching is enabled
    if getattr(CONFIG, "enable_llm_cache", True) and not feedback:
        cached = LLMResponseCache.get(anchor_metric, primary_driver, llm_provider, persona)
        if cached:
            return cached

    # Fast Local/Mock prescriptives when provider is mock or local
    if llm_provider in ["mock", "local"]:
        if "Blue-Sky" in layer:
            proposal = {
                "action_id": "ACT-CHAL-501",
                "action": "Migrate checkout cluster & edge routing to secondary failover infrastructure",
                "source_layer": layer,
                "estimated_cost_usd": 125000.0,
                "time_to_impact_minutes": 120,
                "raci_owner": "CTO / VP Infrastructure",
                "approval_status": "PENDING_VP_APPROVAL",
                "critic_verdict": "APPROVED_LOCAL"
            }
        else:
            if "Stripe" in primary_driver or "Gateway" in primary_driver or "checkout" in anchor_metric.lower():
                action_text = "Roll back Stripe v4.1 integration to v4.0 and re-route 15% traffic to Adyen backup"
                cost = 4200.0
            else:
                action_text = "Execute automated resource scaling and clear service cache pools"
                cost = 1500.0

            proposal = {
                "action_id": f"ACT-{hashlib.md5(action_text.encode()).hexdigest()[:8].upper()}",
                "action": action_text,
                "source_layer": layer,
                "estimated_cost_usd": cost,
                "time_to_impact_minutes": 30,
                "raci_owner": "Platform Engineering",
                "approval_status": "AUTO_APPROVED",
                "critic_verdict": "APPROVED_LOCAL"
            }
        
        LLMResponseCache.set(anchor_metric, primary_driver, llm_provider, persona, proposal)
        return proposal

    llm = get_llm(provider=llm_provider, temperature=temp)
    
    # --- DYNAMIC EXTERNAL WEB INTELLIGENCE AGENT (FinBERT) ---
    web_intelligence = ""
    if len(evidence) <= 1:
        try:
            from kpi_engine.governor.external_tools import WebIntelligenceTools
            web_agent = WebIntelligenceTools()
            ticker = "AAPL"
            news = f"Tech sector crashes as gateway outages spook investors regarding {anchor_metric}."
            report = web_agent.run_external_evaluation(news, ticker)
            web_intelligence = f"\n\n[External Web Agent Report]:\n{report['llm_synthesis']}\n"
        except Exception as e:
            web_intelligence = f"\n\n[External Web Agent Failed]: {str(e)}\n"

    prompt = (
        f"You are the {persona}.\n"
        f"KPI Impacted: {anchor_metric}\n"
        f"Primary Driver: {primary_driver}\n"
        f"{web_intelligence}"
        f"Generate a robust operational solution.\n"
        f"You MUST return your response as a RAW, VALID JSON object with NO markdown formatting, NO intro text, and NO backticks.\n"
        f"Required keys: action, source_layer, estimated_cost_usd, time_to_impact_minutes, raci_owner, approval_status, operational_lever_required.\n"
    )
    if feedback:
        prompt += f"\nPrevious Supervisor Feedback: {feedback}\nAddress this feedback in your new solution."
        
    max_retries = 3
    retry_feedback = ""
    
    for attempt in range(max_retries):
        current_prompt = prompt
        if retry_feedback:
            current_prompt += f"\n\nERROR ON PREVIOUS ATTEMPT:\n{retry_feedback}\nYou MUST fix the JSON formatting error above and return ONLY valid JSON."
            
        response = llm.invoke(current_prompt)
        
        # Extract token usage if available
        tokens_used = 0
        if hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
            token_usage = response.response_metadata.get("token_usage", {})
            if isinstance(token_usage, dict):
                tokens_used = token_usage.get("total_tokens", 500)
            else:
                tokens_used = 500
        else:
            tokens_used = 500
            
        try:
            content = str(response.content).strip()
            
            # Robust regex extraction for JSON block
            import re as std_re
            import ast
            match = std_re.search(r'\{.*\}', content, std_re.DOTALL)
            if match:
                content = match.group(0)
            else:
                raise ValueError("No JSON object found in response.")
            
            try:
                proposal = json.loads(content)
            except Exception:
                try:
                    cleaned = std_re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', content)
                    cleaned = cleaned.replace("true", "True").replace("false", "False").replace("null", "None")
                    proposal = ast.literal_eval(cleaned)
                except Exception as ast_err:
                    raise ValueError(f"Strict JSON and Forgiving AST parsing both failed. {str(ast_err)}")
            
            # Fix hallucinated keys
            if "action" not in proposal:
                for possible_key in ["recommended_action", "mitigation", "fix", "solution", "description", "action_text"]:
                    if possible_key in proposal:
                        proposal["action"] = proposal[possible_key]
                        break
                if "action" not in proposal:
                    # Last resort: grab the first string value that looks long enough to be an action
                    for k, v in proposal.items():
                        if isinstance(v, str) and len(v) > 10:
                            proposal["action"] = v
                            break
            
            action_hash = hashlib.md5(proposal.get("action", "fallback").encode()).hexdigest()[:8].upper()
            proposal["action_id"] = f"ACT-{action_hash}"
            proposal["source_layer"] = layer
            if "critic_verdict" not in proposal:
                proposal["critic_verdict"] = "PENDING_SUPERVISOR"
            
            if not feedback:
                LLMResponseCache.set(anchor_metric, primary_driver, llm_provider, persona, proposal)

            proposal["_tokens_used"] = tokens_used
            return proposal
            
        except Exception as e:
            raw_content = str(response.content) if 'response' in locals() else "No response."
            retry_feedback = f"Error: {str(e)}\nRaw Output:\n{raw_content}"
            if attempt == max_retries - 1:
                err_hash = hashlib.md5(str(e).encode()).hexdigest()[:8].upper()
                return {
                    "action_id": f"ACT-ERR-{err_hash}",
                    "action": f"LLM Error: {str(e)}",
                    "source_layer": layer,
                    "estimated_cost_usd": 0.0,
                    "time_to_impact_minutes": 0,
                    "raci_owner": "SYSTEM",
                    "approval_status": "ERROR",
                    "critic_verdict": f"JSON Parsing Error: {str(e)}"
                }

def rca_story_node(state: AgentState) -> Dict[str, Any]:
    """Generates the primary prescriptive RCA."""
    provider = state.get("primary_llm_provider", "mock")
    proposal = _generate_proposal(state, provider, "Omnision Prescriptive Swarm", "Layer 3 - Prescriptive Swarm", 0.4)
    
    tokens = proposal.pop("_tokens_used", 500)
    proposals = state.get("proposals", [])
    proposals.append(proposal)
    
    return {
        "proposals": proposals,
        "tokens_consumed": state.get("tokens_consumed", 0) + tokens,
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def blue_sky_node(state: AgentState) -> Dict[str, Any]:
    """Generates unconventional, highly creative alternative ideas (Shadow Run)."""
    provider = state.get("bluesky_llm_provider", "mock")
    # Only run Blue-Sky on first iteration to save tokens
    if state.get("blue_sky_iteration", 0) > 0:
        return {}
        
    proposal = _generate_proposal(state, provider, "Blue-Sky Challenger (Creative, Unconstrained)", "Layer 5 - Blue-Sky", 0.9)
    # Flag it for shadow run
    proposal["requires_shadow_run"] = True
    
    tokens = proposal.pop("_tokens_used", 500)
    blue_sky_proposals = state.get("blue_sky_proposals", [])
    blue_sky_proposals.append(proposal)
    
    return {
        "blue_sky_proposals": blue_sky_proposals,
        "tokens_consumed": state.get("tokens_consumed", 0) + tokens,
        "blue_sky_iteration": state.get("blue_sky_iteration", 0) + 1
    }





