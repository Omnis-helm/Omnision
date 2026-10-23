"""
Swarm generators: RCA storytelling + prescriptive proposals (primary) and Blue-Sky challenger.

The LLM is "caged": it only sees the bounded, scored causal evidence, retrieved precedents and the
grounded playbook candidates, and must answer in JSON. With the `mock` / `local` providers no LLM is
called; the narrative is built from the same evidence by a deterministic template.
"""
import json
import re
import ast
from typing import Dict, Any, List, Tuple, Optional

from kpi_engine.governor.llm_factory import get_llm, extract_usage, LLMProviderError
from kpi_engine.ml.local_ml_engine import LLMResponseCache
from kpi_engine.config import CONFIG

LOCAL_PROVIDERS = ("mock", "local")


# ----------------------------------------------------------------------------- narrative
def _fmt_num(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def build_narrative_template(anchor: Dict[str, Any], evidence: List[Dict[str, Any]],
                             history: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
    """Deterministic KPI story assembled only from scored evidence (no free text invented)."""
    metric = anchor.get("metric_name", "The KPI")
    var = anchor.get("variance_pct", 0.0)
    direction = "fell" if var < 0 else "rose"
    z = anchor.get("z_score", 0.0)
    severity = "a severe shock" if z >= CONFIG.z_score_shock_threshold else "a statistically significant anomaly"
    stage = anchor.get("lifecycle_stage", "MATURE")
    rule = anchor.get("trigger_rule", "")
    baseline = anchor.get("baseline_mean")
    current = anchor.get("current_value")

    if stage == "COLD_START":
        severity = f"breaching the {CONFIG.cold_start_static_tripwire:.0%} cold-start tripwire"
    parts = [f"{metric} {direction} {abs(var):.1f}% to {_fmt_num(current)} against a baseline of {_fmt_num(baseline)} "
             f"(Z = {z:.2f}, {severity}; {stage.lower().replace('_', '-')} KPI, rule {rule})."]
    if stage == "COLD_START":
        parts.append("With fewer than 30 days of history the baseline comes from an EWMA blended with a mature "
                     "surrogate KPI, so the 5% static tripwire fired rather than a full Z-score test.")

    drivers = [e for e in evidence if e.get("hop", 1) == 1]
    upstream = [e for e in evidence if e.get("hop", 1) >= 2]
    if drivers:
        d0 = drivers[0]
        parts.append(f"The strongest causal driver is **{d0['title']}**: {d0['content']} "
                     f"(composite weight W = {d0.get('causal_weight', 0):.2f}, {d0.get('tier', '')}).")
        for d in drivers[1:3]:
            parts.append(f"It is compounded by **{d['title']}** (W = {d.get('causal_weight', 0):.2f}): {d['content']}.")
    else:
        parts.append("No candidate evidence cleared the causal threshold; the drop is currently unexplained.")
    for u in upstream[:3]:
        verb = "corroborated by" if u.get("relation") == "corroborates" else "in turn driven by"
        parts.append(f"That driver is {verb} **{u['title']}** ({u['content']}).")

    shap = context.get("shap_attribution") or {}
    if shap.get("relative_attribution_pct"):
        top = sorted(shap["relative_attribution_pct"].items(), key=lambda kv: -abs(kv[1]))[:3]
        parts.append("The global model attributes the ambient pressure to " +
                     ", ".join(f"{k.replace('_', ' ')} ({v:+.0f}%)" for k, v in top) + ".")
    dag = context.get("metric_tree_math")
    if dag:
        parts.append(f"Metric-tree math: price effect {_fmt_money(dag['price_effect_usd'])}, volume effect "
                     f"{_fmt_money(dag['volume_effect_usd'])}, interaction {_fmt_money(dag['interaction_effect_usd'])} "
                     f"(total {_fmt_money(dag['total_delta_r_usd'])}).")

    for h in history[:1]:
        kind = "known false-alarm signature" if h.get("node_type") == "Historical_Noise" else "past incident"
        parts.append(f"Institutional memory recalls a similar {kind} ({h.get('historical_id')}, similarity "
                     f"{h.get('similarity', 0):.2f}): {h['content']}")

    ruled_out = context.get("ruled_out_titles") or []
    if ruled_out:
        parts.append("Ruled out: " + "; ".join(ruled_out[:4]) + ".")
    if context.get("financial_impact_usd"):
        parts.append(f"Estimated financial exposure: {_fmt_money(float(context['financial_impact_usd']))}.")
    return " ".join(parts)


# ----------------------------------------------------------------------------- JSON parsing
def parse_json_object(content: str) -> Any:
    content = str(content).strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response.")
    raw = match.group(1)
    try:
        return json.loads(raw)
    except Exception:
        cleaned = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', raw)
        cleaned = cleaned.replace("true", "True").replace("false", "False").replace("null", "None")
        return ast.literal_eval(cleaned)


ACTION_KEYS = ("action", "recommended_action", "mitigation", "fix", "solution", "description", "action_text")


def normalize_proposal(p: Dict[str, Any], source_layer: str) -> Optional[Dict[str, Any]]:
    if not isinstance(p, dict):
        return None
    action = next((p[k] for k in ACTION_KEYS if isinstance(p.get(k), str) and p.get(k).strip()), None)
    if not action:
        return None

    def num(k, default, cast):
        try:
            return cast(str(p.get(k, default)).replace("$", "").replace(",", ""))
        except Exception:
            return default

    lever = p.get("operational_lever_required") or None
    if isinstance(lever, str) and lever.strip().lower() in ("", "none", "null", "n/a"):
        lever = None
    return {
        "action": action.strip(),
        "source_layer": source_layer,
        "estimated_cost_usd": num("estimated_cost_usd", 0.0, float),
        "time_to_impact_minutes": num("time_to_impact_minutes", 60, lambda x: int(float(x))),
        "raci_owner": str(p.get("raci_owner") or "Unassigned"),
        "operational_lever_required": lever,
        "technical_command": p.get("technical_command") or p.get("command"),
        "addresses_node_id": p.get("addresses_node_id"),
        "rationale": p.get("rationale", ""),
    }


# ----------------------------------------------------------------------------- prompts
def _evidence_block(evidence: List[Dict[str, Any]]) -> str:
    lines = []
    for e in evidence[:8]:
        lines.append(f"- [{e['node_id']}] (W={e.get('causal_weight', 0):.2f}, hop {e.get('hop', 1)}, "
                     f"{e.get('relation', 'causes')}) {e['title']}: {e['content']}")
    return "\n".join(lines) or "- (none)"


def build_primary_prompt(state: Dict[str, Any], grounded: List[Dict[str, Any]], levers: Dict[str, bool]) -> str:
    anchor = state["anchor_context"]
    ctx = state.get("context", {})
    rejected = [r.get("action") for r in state.get("rejected_proposals", [])] + list(ctx.get("rejected_actions", []))
    history = state.get("historical_context", [])
    return (
        "You are the Omnision Prescriptive Swarm, an incident commander for business KPIs.\n"
        "Reason ONLY from the evidence below. Do not invent causes.\n\n"
        f"KPI: {anchor['metric_name']} changed {anchor['variance_pct']:+.2f}% (Z={anchor['z_score']:.2f}, "
        f"baseline {anchor['baseline_mean']}, current {anchor['current_value']}).\n\n"
        f"Causal evidence (strongest first):\n{_evidence_block(state.get('causal_evidence', []))}\n\n"
        "Historical precedents:\n" + ("\n".join(f"- {h['content']}" for h in history[:2]) or "- (none)") + "\n\n"
        "Grounded playbook candidates already available:\n" +
        ("\n".join(f"- {g['action']} (cost ${g['estimated_cost_usd']:,.0f}, lever {g.get('operational_lever_required')})"
                   for g in grounded[:5]) or "- (none)") + "\n\n"
        f"Active operational levers you may require (or null): {[k for k, v in levers.items() if v]}\n"
        f"RACI: <= ${CONFIG.auto_approve_cost_ceiling_usd:,.0f} auto-approved, > ${CONFIG.vp_approval_required_cost_usd:,.0f} needs VP. "
        f"Fixes must act within {CONFIG.max_time_to_impact_minutes} minutes.\n"
        + (f"Do NOT propose these rejected actions again: {rejected}\n" if rejected else "")
        + (f"Supervisor feedback on the previous attempt: {state.get('supervisor_feedback')}\n" if state.get("supervisor_feedback") and state.get("iteration_count", 0) > 0 else "")
        + "\nReturn ONLY raw JSON (no markdown) of the form:\n"
        '{"narrative": "4-6 sentence executive story of what happened and why, citing node ids",'
        ' "proposals": [{"action": "...", "addresses_node_id": "NODE-...", "estimated_cost_usd": 0,'
        ' "time_to_impact_minutes": 30, "raci_owner": "...", "operational_lever_required": "lever or null",'
        ' "technical_command": "...", "rationale": "..."}]}\n'
        "Give 1-3 proposals."
    )


def build_bluesky_prompt(state: Dict[str, Any]) -> str:
    anchor = state["anchor_context"]
    return (
        "You are the Blue-Sky Challenger: an unconstrained turnaround CEO. Propose ONE bold, strategic alternative "
        "to the operational fixes, addressing the root cause below.\n"
        f"KPI: {anchor['metric_name']} ({anchor['variance_pct']:+.2f}%).\n"
        f"Causal evidence:\n{_evidence_block(state.get('causal_evidence', []))}\n"
        'Return ONLY raw JSON: {"proposals": [{"action": "...", "estimated_cost_usd": 0, '
        '"time_to_impact_minutes": 0, "raci_owner": "...", "operational_lever_required": null, "rationale": "..."}]}'
    )


def call_llm_json(provider: str, prompt: str, temperature: float, cache_parts: Tuple, use_cache: bool
                  ) -> Tuple[Any, int, int, bool]:
    """Invoke the provider with up to 2 repair retries. Returns (parsed_json, in_tokens, out_tokens, cache_hit)."""
    key = LLMResponseCache.make_key(provider, prompt, temperature, *cache_parts)
    if use_cache and CONFIG.enable_llm_cache:
        cached = LLMResponseCache.get(key)
        if cached is not None:
            return cached, 0, 0, True

    llm = get_llm(provider=provider, temperature=temperature)
    tin = tout = 0
    last_err = None
    current = prompt
    for _ in range(3):
        try:
            response = llm.invoke(current)
        except Exception as e:  # network / auth / quota
            raise LLMProviderError(f"{provider} call failed: {e}") from e
        i, o = extract_usage(response, current)
        tin, tout = tin + i, tout + o
        try:
            parsed = parse_json_object(getattr(response, "content", response))
            LLMResponseCache.set(key, parsed)
            return parsed, tin, tout, False
        except Exception as e:
            last_err = e
            current = prompt + f"\n\nYour previous answer was not valid JSON ({e}). Return ONLY the JSON object."
    raise LLMProviderError(f"{provider} returned unparseable output: {last_err}")
