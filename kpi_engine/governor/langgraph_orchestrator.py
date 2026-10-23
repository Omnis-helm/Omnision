"""
LangGraph Orchestrator for the Causal Mitigation Swarm (Stages 5 & 6)

                       ┌──────────────► blue_sky_agent ──► blue_sky_critic ──► END   (sandbox, never loops)
  START ─► rca_agent ──┤
                       └──────────────► deterministic_validator ─► llm_supervisor ─┐
                ▲                                                                   │ REJECTED (< max iters)
                └───────────────────────────────────────────────────────────────────┘
                                                        APPROVED / MAX_ITERATIONS ─► END

rca_agent               Channel A grounded playbooks (Layers 1-3) + optional LLM proposals + narrative
deterministic_validator The Critic: security, correctness, liveness, lever feasibility, time, RACI
llm_supervisor          semantic / LLM alignment review; rejection feeds back to rca_agent
blue_sky_agent          Channel B challenger idea; blue_sky_critic gives a non-punishing critique

If LangGraph is not installed (or fails) the identical node functions run sequentially.
"""
import hashlib
import logging
from types import SimpleNamespace
from typing import Dict, Any, List, Optional

from kpi_engine.config import CONFIG
from kpi_engine.data.models import UserClearance
from kpi_engine.governor.llm_state import AgentState, merge_state
from kpi_engine.governor.critic import TheCritic
from kpi_engine.governor.hybrid_supervisor import review_proposals, critique_blue_sky, driver_texts
from kpi_engine.suggester.dual_channel import DualChannelSuggester, agent_for_layer
from kpi_engine.suggester.layers_data import PrescriptiveLayersStore, SolutionCandidate
from kpi_engine.suggester.llm_swarm import (
    LOCAL_PROVIDERS, build_narrative_template, build_primary_prompt, build_bluesky_prompt,
    call_llm_json, normalize_proposal,
)

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "__end__"


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def _cand_to_dict(c: SolutionCandidate, iteration: int) -> Dict[str, Any]:
    d = c.model_dump()
    d["iteration"] = iteration
    return d


class SwarmOrchestrator:
    """Binds the swarm graph to one engine's playbook store, critic and trust weights."""

    def __init__(self, layers_store: Optional[PrescriptiveLayersStore] = None,
                 trust_weights: Optional[Dict[str, float]] = None, config=CONFIG):
        self.config = config
        self.store = layers_store or PrescriptiveLayersStore()
        self.trust_weights = trust_weights if trust_weights is not None else {}
        self.suggester = DualChannelSuggester(self.store, self.trust_weights)
        self.critic = TheCritic(self.store, config)
        self.mode = "langgraph" if LANGGRAPH_AVAILABLE else "sequential"

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _anchor_ns(state):
        return SimpleNamespace(**state["anchor_context"])

    @staticmethod
    def _role(state) -> UserClearance:
        try:
            return UserClearance(state.get("user_role", "EXECUTIVE_VP"))
        except ValueError:
            return UserClearance.PUBLIC

    def _fallback_proposal(self, state, iteration: int) -> Dict[str, Any]:
        metric = state["anchor_context"].get("metric_name", "the KPI")
        action = (f"Initiate manual incident triage for {metric}: page the on-call incident commander "
                  f"with the causal evidence pack")
        return {
            "action_id": "ACT-FALLBACK-001", "action": action,
            "source_layer": "Layer 1 - Emergency Fallback Runbook", "model_confidence_weight": 0.5,
            "estimated_cost_usd": 0.0, "time_to_impact_minutes": 10, "raci_owner": "On-Call Incident Commander",
            "approval_status": "AUTO_APPROVED", "critic_verdict": "PASS - Circuit-breaker fallback (no automated fix survived governance).",
            "supervisor_verdict": "APPROVED - fallback", "technical_command": "pagerduty trigger --service kpi-incident --severity high",
            "target_environment": "incident-mgmt", "operational_lever_required": None, "addresses_node_id": None,
            "match_score": 0.0, "agent_key": "tech_agent", "is_fallback": True, "iteration": iteration,
            "status": "APPROVED",
        }

    def _seen(self, state) -> set:
        seen = {_norm(p.get("action")) for p in state.get("proposals", [])}
        seen |= {_norm(a) for a in state.get("context", {}).get("rejected_actions", [])}
        return seen

    # ------------------------------------------------------------------ primary channel
    def rca_agent(self, state: AgentState) -> Dict[str, Any]:
        it = state.get("iteration_count", 0) + 1
        provider = state.get("primary_llm_provider", "mock")
        evidence = state.get("causal_evidence", [])
        use_cache = not state.get("context", {}).get("force_refresh", False)
        update: Dict[str, Any] = {"iteration_count": it, "tokens_input": 0, "tokens_output": 0,
                                  "cache_hits": 0, "llm_errors": []}
        seen = self._seen(state)

        grounded = [_cand_to_dict(c, it) for c in
                    self.suggester.run_channel_a_grounded(self._anchor_ns(state), evidence, self._role(state))]
        grounded = [g for g in grounded if _norm(g["action"]) not in seen]

        llm_props: List[Dict[str, Any]] = []
        llm_narrative = ""
        if provider not in LOCAL_PROVIDERS:
            try:
                prompt = build_primary_prompt(state, grounded, self.store.layer_3_active_levers)
                parsed, tin, tout, hit = call_llm_json(provider, prompt, 0.3, ("primary", it), use_cache)
                update["tokens_input"] += tin
                update["tokens_output"] += tout
                update["cache_hits"] += int(hit)
                raw = parsed.get("proposals", []) if isinstance(parsed, dict) else parsed
                llm_narrative = (parsed.get("narrative") or "").strip() if isinstance(parsed, dict) else ""
                label = f"LLM Prescriptive Swarm ({provider})"
                trust = self.trust_weights.get("llm_swarm_agent", 0.85)
                for p in raw[:3]:
                    n = normalize_proposal(p, label)
                    if n and _norm(n["action"]) not in seen:
                        n.update({"action_id": f"ACT-LLM-{hashlib.md5(n['action'].encode()).hexdigest()[:8].upper()}",
                                  "agent_key": agent_for_layer(label), "model_confidence_weight": round(trust * 0.9, 4),
                                  "match_score": 0.0, "approval_status": "PENDING_REVIEW", "iteration": it,
                                  "target_environment": None})
                        llm_props.append(n)
            except Exception as e:
                update["llm_errors"] = [f"Primary LLM ({provider}) failed; continuing with grounded playbooks: {e}"]

        batch = (llm_props + grounded)[:4]
        if not batch:
            batch = [self._fallback_proposal(state, it)]
        update["candidate_pool"] = batch

        if not state.get("narrative"):
            if llm_narrative:
                update["narrative"], update["narrative_source"] = llm_narrative, f"LLM ({provider})"
            else:
                update["narrative"] = build_narrative_template(
                    state["anchor_context"], evidence, state.get("historical_context", []), state.get("context", {}))
                update["narrative_source"] = "Deterministic template (evidence-grounded)"
        return update

    def deterministic_validator(self, state: AgentState) -> Dict[str, Any]:
        it = state.get("iteration_count", 0)
        batch = [dict(p) for p in state.get("candidate_pool", [])]
        texts = driver_texts(state.get("causal_evidence", []))
        passed, rejected = [], []
        for p in batch:
            if p.get("is_fallback"):
                passed.append(p)
                continue
            cand = SolutionCandidate(**{k: v for k, v in p.items() if k in SolutionCandidate.model_fields})
            ok, note = self.critic.evaluate_one(cand, texts)
            if ok:
                p["approval_status"], p["critic_verdict"] = self.critic.approval_status_for_cost(cand.estimated_cost_usd)
                p["alignment_note"] = note
                passed.append(p)
            else:
                p.update({"approval_status": "DISCARDED", "critic_verdict": note, "status": "REJECTED",
                          "rejected_by": "Critic"})
                rejected.append(p)

        update = {
            "proposals": list(state.get("proposals", [])) + batch,
            "rejected_proposals": list(state.get("rejected_proposals", [])) + rejected,
            "pending_review": passed,
        }
        if passed:
            update["final_status"] = "PENDING_LLM_REVIEW"
            update["supervisor_feedback"] = f"{len(passed)} of {len(batch)} proposals passed the Critic."
            return update

        reasons = "; ".join(f"'{p['action'][:60]}': {p['critic_verdict']}" for p in rejected)
        if it >= self.config.swarm_max_iterations:
            fb = self._fallback_proposal(state, it)
            update.update({"final_status": "MAX_ITERATIONS_REACHED", "pending_review": [],
                           "approved_proposals": list(state.get("approved_proposals", [])) + [fb],
                           "supervisor_feedback": f"Max iterations ({it}) reached. Critic rejected: {reasons}"})
        else:
            update.update({"final_status": "REJECTED", "supervisor_feedback": f"Critic rejected all proposals: {reasons}"})
        return update

    def llm_supervisor(self, state: AgentState) -> Dict[str, Any]:
        if state.get("final_status") != "PENDING_LLM_REVIEW":
            return {}
        it = state.get("iteration_count", 0)
        pending = [dict(p) for p in state.get("pending_review", [])]
        provider = state.get("primary_llm_provider", "mock")
        use_cache = not state.get("context", {}).get("force_refresh", False)
        res = review_proposals(provider, state["anchor_context"], state.get("causal_evidence", []), pending, use_cache)

        approved, rejected = [], []
        for p, (decision, reason, score) in zip(pending, res["verdicts"]):
            p["supervisor_verdict"] = f"{decision} - {reason}"
            p["alignment_score"] = round(score, 4)
            if decision == "APPROVED":
                p["status"] = "APPROVED"
                approved.append(p)
            else:
                p.update({"status": "REJECTED", "approval_status": "DISCARDED", "rejected_by": "Supervisor",
                          "critic_verdict": f"REJECTED by Supervisor: {reason}"})
                rejected.append(p)

        update = {
            "approved_proposals": list(state.get("approved_proposals", [])) + approved,
            "rejected_proposals": list(state.get("rejected_proposals", [])) + rejected,
            "pending_review": [],
            "tokens_input": res["tokens_input"], "tokens_output": res["tokens_output"],
            "cache_hits": res["cache_hits"], "llm_errors": res["llm_errors"],
        }
        if approved:
            update["final_status"] = "APPROVED"
            update["supervisor_feedback"] = f"Supervisor approved {len(approved)} action(s); rejected {len(rejected)}."
        elif it >= self.config.swarm_max_iterations:
            update["final_status"] = "MAX_ITERATIONS_REACHED"
            update["approved_proposals"] = update["approved_proposals"] + [self._fallback_proposal(state, it)]
            update["supervisor_feedback"] = "Max iterations reached; escalating to manual triage."
        else:
            update["final_status"] = "REJECTED"
            update["supervisor_feedback"] = "Supervisor rejected: " + "; ".join(
                f"'{p['action'][:60]}' ({p['supervisor_verdict']})" for p in rejected)
        return update

    # ------------------------------------------------------------------ blue-sky channel
    def blue_sky_agent(self, state: AgentState) -> Dict[str, Any]:
        if state.get("blue_sky_iteration", 0) > 0:
            return {}
        provider = state.get("bluesky_llm_provider", "mock")
        evidence = state.get("causal_evidence", [])
        update: Dict[str, Any] = {"blue_sky_iteration": 1, "tokens_input": 0, "tokens_output": 0,
                                  "cache_hits": 0, "llm_errors": []}
        proposals: List[Dict[str, Any]] = []
        if provider not in LOCAL_PROVIDERS:
            try:
                parsed, tin, tout, hit = call_llm_json(provider, build_bluesky_prompt(state), 0.9, ("bluesky",),
                                                       not state.get("context", {}).get("force_refresh", False))
                update.update({"tokens_input": tin, "tokens_output": tout, "cache_hits": int(hit)})
                raw = parsed.get("proposals", []) if isinstance(parsed, dict) else parsed
                label = f"Layer 5 - Blue-Sky Challenger ({provider})"
                for p in raw[:1]:
                    n = normalize_proposal(p, label)
                    if n:
                        n.update({"action_id": f"ACT-CHAL-{hashlib.md5(n['action'].encode()).hexdigest()[:6].upper()}",
                                  "agent_key": "challenger_agent", "requires_shadow_run": True, "match_score": 0.0,
                                  "model_confidence_weight": self.trust_weights.get("challenger_agent", 0.65),
                                  "approval_status": "SANDBOX", "target_environment": "sandbox"})
                        proposals.append(n)
            except Exception as e:
                update["llm_errors"] = [f"Blue-Sky LLM ({provider}) failed; using template challenger: {e}"]
        if not proposals:
            proposals = [c.model_dump() for c in
                         self.suggester.run_channel_b_challenger(self._anchor_ns(state), evidence, self._role(state))]
        update["blue_sky_proposals"] = proposals
        return update

    def blue_sky_critic(self, state: AgentState) -> Dict[str, Any]:
        props = [dict(p) for p in state.get("blue_sky_proposals", [])]
        if not props or state.get("blue_sky_critique"):
            return {}
        provider = state.get("bluesky_llm_provider", "mock")
        texts = driver_texts(state.get("causal_evidence", []))
        critiques, errors, tin_t, tout_t = [], [], 0, 0
        for p in props:
            cand = SolutionCandidate(**{k: v for k, v in p.items() if k in SolutionCandidate.model_fields})
            ok, note = self.critic.evaluate_one(cand, texts, is_blue_sky=True)
            note = note if note.startswith(("SANDBOX", "REJECTED")) else "SANDBOX - Passed safety checks."
            text, tin, tout, errs = critique_blue_sky(provider, p, note,
                                                      not state.get("context", {}).get("force_refresh", False))
            p["critic_verdict"] = text
            p["approval_status"] = "SANDBOX" if ok else "BLOCKED_BY_GUARDRAIL"
            critiques.append(text)
            errors += errs
            tin_t += tin
            tout_t += tout
        return {"blue_sky_proposals": props, "blue_sky_critique": " | ".join(critiques),
                "tokens_input": tin_t, "tokens_output": tout_t, "llm_errors": errors}

    # ------------------------------------------------------------------ execution
    @staticmethod
    def route_supervisor(state: AgentState) -> str:
        return END if state.get("final_status") in ("APPROVED", "MAX_ITERATIONS_REACHED") else "rca_agent"

    def _compile(self):
        wf = StateGraph(AgentState)
        wf.add_node("rca_agent", self.rca_agent)
        wf.add_node("blue_sky_agent", self.blue_sky_agent)
        wf.add_node("deterministic_validator", self.deterministic_validator)
        wf.add_node("llm_supervisor", self.llm_supervisor)
        wf.add_node("blue_sky_critic", self.blue_sky_critic)
        wf.set_entry_point("rca_agent")
        wf.add_edge("rca_agent", "deterministic_validator")
        wf.add_edge("rca_agent", "blue_sky_agent")
        wf.add_edge("blue_sky_agent", "blue_sky_critic")
        wf.add_edge("blue_sky_critic", END)
        wf.add_edge("deterministic_validator", "llm_supervisor")
        wf.add_conditional_edges("llm_supervisor", self.route_supervisor, {END: END, "rca_agent": "rca_agent"})
        return wf.compile()

    def _run_sequential(self, state: Dict[str, Any]) -> Dict[str, Any]:
        merge_state(state, self.rca_agent(state))
        merge_state(state, self.blue_sky_agent(state))
        merge_state(state, self.blue_sky_critic(state))
        while True:
            merge_state(state, self.deterministic_validator(state))
            merge_state(state, self.llm_supervisor(state))
            if self.route_supervisor(state) == END:
                return state
            merge_state(state, self.rca_agent(state))

    def execute(self, anchor: Dict[str, Any], causal_evidence: List[Dict[str, Any]], context: Dict[str, Any],
                historical_context: Optional[List[Dict[str, Any]]] = None, user_role: str = "EXECUTIVE_VP",
                primary_llm: str = "mock", bluesky_llm: str = "mock") -> Dict[str, Any]:
        initial = {
            "anchor_context": anchor, "causal_evidence": causal_evidence,
            "historical_context": historical_context or [], "context": context, "user_role": user_role,
            "primary_llm_provider": primary_llm, "bluesky_llm_provider": bluesky_llm,
            "candidate_pool": [], "pending_review": [], "proposals": [], "approved_proposals": [],
            "rejected_proposals": [], "narrative": "", "narrative_source": "",
            "blue_sky_proposals": [], "blue_sky_critique": "", "blue_sky_iteration": 0,
            "supervisor_feedback": None, "iteration_count": 0, "final_status": "PENDING",
            "tokens_input": 0, "tokens_output": 0, "cache_hits": 0, "llm_errors": [],
        }
        if LANGGRAPH_AVAILABLE:
            try:
                final = dict(self._compile().invoke(initial, {"recursion_limit": 50}))
                final["orchestration_mode"] = "langgraph"
                return final
            except Exception as e:
                logger.warning("LangGraph execution failed, falling back to sequential execution: %s", e)
        final = self._run_sequential(dict(initial))
        final["orchestration_mode"] = "sequential"
        return final


def execute_langgraph_swarm(anchor: Dict[str, Any], causal_evidence: List[Dict[str, Any]], context: Dict[str, Any],
                            **kwargs) -> Dict[str, Any]:
    """Backward-compatible functional entry point using a default playbook store."""
    return SwarmOrchestrator().execute(
        anchor, causal_evidence, context,
        primary_llm=context.get("primary_llm_provider", "mock"),
        bluesky_llm=context.get("bluesky_llm_provider", "mock"), **kwargs)
