"""
Hybrid Neuro-Symbolic Supervisor

Layer 2 of governance (after the deterministic Critic): checks that each surviving proposal is
logically aligned with the causal evidence.
  * mock / local / unreachable LLM -> LocalSemanticSupervisor (deterministic semantic alignment)
  * cloud or Ollama provider       -> LLM review in strict JSON; any error falls back to the local check
                                      (fail closed: an error is never an approval)
"""
from typing import Dict, Any, List, Tuple

from kpi_engine.config import CONFIG
from kpi_engine.ml.local_ml_engine import LocalSemanticSupervisor
from kpi_engine.suggester.llm_swarm import call_llm_json, LOCAL_PROVIDERS


def driver_texts(evidence: List[Dict[str, Any]]) -> List[str]:
    """Ranked causal chain texts (hop-1 drivers first, then their upstream causes)."""
    ranked = sorted(evidence, key=lambda e: (e.get("hop", 1), -e.get("causal_weight", 0.0)))
    return [f"{e.get('title', '')} {e.get('content', '')}" for e in ranked[:5]]


def local_review(evidence: List[Dict[str, Any]], proposals: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
    texts = driver_texts(evidence)
    evidence_ids = {e.get("node_id") for e in evidence}
    thr = CONFIG.supervisor_alignment_threshold
    out = []
    for p in proposals:
        if p.get("is_fallback"):
            out.append(("APPROVED", "Circuit-breaker fallback: manual triage is always permitted.", 1.0))
            continue
        decision, reason, score = LocalSemanticSupervisor.evaluate_alignment(texts, p.get("action", ""), thr)
        grounded = p.get("match_score", 0.0) if p.get("addresses_node_id") in evidence_ids else 0.0
        if decision != "APPROVED" and grounded >= thr:
            decision = "APPROVED"
            reason = (f"Grounded playbook match to {p['addresses_node_id']} (trigger match {grounded:.2f}); "
                      f"semantic score {score:.2f}.")
            score = max(score, grounded)
        out.append((decision, reason, score))
    return out


def llm_review(provider: str, anchor: Dict[str, Any], evidence: List[Dict[str, Any]],
               proposals: List[Dict[str, Any]], use_cache: bool) -> Tuple[List[Tuple[str, str, float]], int, int, bool]:
    causes = "\n".join(f"- [{e['node_id']}] {e['title']}: {e['content']}" for e in evidence[:5])
    items = "\n".join(f"{i}. {p['action']}" for i, p in enumerate(proposals))
    prompt = (
        "You are the Omnision Chief Supervisor. For each proposed action decide whether it logically "
        "neutralises the causal root cause of the KPI anomaly. Reject actions that address something else.\n"
        f"KPI: {anchor.get('metric_name')} ({anchor.get('variance_pct', 0):+.2f}%)\n"
        f"Causal evidence:\n{causes}\n\nProposed actions:\n{items}\n\n"
        'Respond ONLY with raw JSON: {"reviews": [{"index": 0, "decision": "APPROVED" or "REJECTED", "reason": "..."}]}'
    )
    parsed, tin, tout, hit = call_llm_json(provider, prompt, 0.0, ("supervisor",), use_cache)
    reviews = parsed.get("reviews", []) if isinstance(parsed, dict) else parsed
    by_idx = {int(r.get("index", -1)): r for r in reviews if isinstance(r, dict)}
    local = local_review(evidence, proposals)
    out = []
    for i, p in enumerate(proposals):
        r = by_idx.get(i)
        if r is None:  # model skipped it -> deterministic check
            out.append(local[i])
            continue
        decision = "APPROVED" if str(r.get("decision", "")).upper().startswith("APPROV") else "REJECTED"
        out.append((decision, f"[LLM Supervisor] {r.get('reason', '')}", local[i][2]))
    return out, tin, tout, hit


def review_proposals(provider: str, anchor: Dict[str, Any], evidence: List[Dict[str, Any]],
                     proposals: List[Dict[str, Any]], use_cache: bool = True) -> Dict[str, Any]:
    """Returns {'verdicts': [(decision, reason, score)], tokens_input, tokens_output, cache_hits, llm_errors}."""
    if provider in LOCAL_PROVIDERS:
        return {"verdicts": local_review(evidence, proposals), "tokens_input": 0, "tokens_output": 0,
                "cache_hits": 0, "llm_errors": []}
    try:
        verdicts, tin, tout, hit = llm_review(provider, anchor, evidence, proposals, use_cache)
        return {"verdicts": verdicts, "tokens_input": tin, "tokens_output": tout, "cache_hits": int(hit), "llm_errors": []}
    except Exception as e:
        return {"verdicts": local_review(evidence, proposals), "tokens_input": 0, "tokens_output": 0, "cache_hits": 0,
                "llm_errors": [f"Supervisor LLM ({provider}) unavailable, used local semantic check: {e}"]}


def critique_blue_sky(provider: str, proposal: Dict[str, Any], critic_note: str, use_cache: bool = True
                      ) -> Tuple[str, int, int, List[str]]:
    """Non-punishing Reality Checker critique (never rejects or loops)."""
    cost = float(proposal.get("estimated_cost_usd", 0))
    minutes = int(proposal.get("time_to_impact_minutes", 0))
    base = (f"{critic_note} Estimated cost ${cost:,.0f} "
            f"({'above' if cost > CONFIG.vp_approval_required_cost_usd else 'within'} the VP ceiling); "
            f"time to impact {minutes / 60:.0f}h "
            f"({'outside' if minutes > CONFIG.max_time_to_impact_minutes else 'inside'} the incident window). "
            "Treat as a strategic option to validate in a shadow run, not as the incident fix.")
    if provider in LOCAL_PROVIDERS:
        return base, 0, 0, []
    try:
        prompt = (f"You are the Omnision Reality Checker. Critique this Blue-Sky idea in 1-2 sentences "
                  f"(feasibility, risk). Do not reject it.\nIdea: {proposal.get('action')}\n"
                  'Respond ONLY with raw JSON: {"critique": "..."}')
        parsed, tin, tout, _ = call_llm_json(provider, prompt, 0.2, ("bluesky_critic",), use_cache)
        return f"{parsed.get('critique', '').strip()} — {base}", tin, tout, []
    except Exception as e:
        return base, 0, 0, [f"Blue-Sky critic LLM ({provider}) unavailable: {e}"]
