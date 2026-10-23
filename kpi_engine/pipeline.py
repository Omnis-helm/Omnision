"""
End-to-End Orchestration Pipeline for the Omnision KPI Storytelling Engine.

Stage 0  Heterogeneous ingestion + reconciliation (global model training data)
Stage 1  Detection: Z-score / systemic drift / cold-start phased handover -> Anchor A*
Stage 2  Directional scoping + Hybrid Security Matrix (Tier 1 pruning / Tier 2 masking / abstention)
Stage 3  Bounded graph: The Cage (time + dimensions + Graph-RAG memory) and The Brakes (threshold, hops)
Stage 4  Composite causal scoring W = CR x CI (metric-tree math, DiD, CI bands, SHAP on the global model)
Stage 5  Dual-channel suggestion network (grounded playbooks / levers / precedents + Blue-Sky challenger)
Stage 6  LangGraph swarm governance (Critic -> Supervisor loop with feedback) + persona payloads
Stage 7  Closed-loop learning: RCA overrides, noise flags, rejected fixes, trust tuning, playbook appends
"""

import copy
import time
import uuid
from typing import Dict, Any, List, Optional, Set

from kpi_engine.config import CONFIG
from kpi_engine.auth import assert_providers_allowed, is_public_provider
from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType, UserClearance, SecurityTier
from kpi_engine.data.generator import KartMitraDataGenerator
from kpi_engine.data.reconciler import HeterogeneousDataReconciler
from kpi_engine.data.seed_scenarios import (
    get_scenario_1_stripe_outage,
    get_scenario_2_multivariate_price_volume,
    get_scenario_3_cold_start_kpi,
    get_scenario_4_security_clearance,
)
from kpi_engine.detector.anomaly_pipeline import TelemetryAnomalyDetector
from kpi_engine.scoper.directional_router import DirectionalScoper
from kpi_engine.scoper.security_matrix import HybridSecurityMatrix
from kpi_engine.memory.vector_store import PlaybookVectorStore
from kpi_engine.graph.bounded_builder import BoundedGraphBuilder
from kpi_engine.causal.composite_scorer import CompositeCausalScorer, is_historical
from kpi_engine.causal.contextual_relevance import ContextualRelevanceScorer
from kpi_engine.suggester.layers_data import PrescriptiveLayersStore
from kpi_engine.governor.supervisor import SupervisorFramework
from kpi_engine.governor.schemas import (
    UnifiedMasterPayload, AnchorReferenceBlock, RuntimeMetadataBlock, DiscardedCandidateBlock,
)
from kpi_engine.governor.external_tools import WebIntelligenceTools, web_intelligence_enabled
from kpi_engine.learning.rca_corrections import RCACorrectionManager
from kpi_engine.learning.trust_tuning import ModelTrustTuner
from kpi_engine.learning.dynamic_playbook import DynamicPlaybookAppender
from kpi_engine.ml.global_model import GlobalKPIModel

SCENARIOS = {
    "SCENARIO_1_STRIPE_GATEWAY_OUTAGE": get_scenario_1_stripe_outage,
    "SCENARIO_2_MULTIVARIATE_DAG_SHAP": get_scenario_2_multivariate_price_volume,
    "SCENARIO_3_COLD_START_PHASED_HANDOVER": get_scenario_3_cold_start_kpi,
    "SCENARIO_4_SECURITY_CLEARANCE_MATRIX": get_scenario_4_security_clearance,
}


class KPIStorytellingEngine:
    """The master pipeline orchestrating all architectural stages."""

    def __init__(self, config=CONFIG):
        self.config = config

        # Stage 0 & 1: data + detection
        self.data_generator = KartMitraDataGenerator()
        self.contracts = self.data_generator.generate_contracts()
        self.telemetry_series, self.base_time = self.data_generator.generate_telemetry_series(days=35)
        self.detector = TelemetryAnomalyDetector(config)
        self.cold_start_mgr = self.detector.cold_start_mgr

        # Stage 2
        self.scoper = DirectionalScoper()
        self.security_matrix = HybridSecurityMatrix()

        # Stage 3 & 4 (one shared CR scorer so human recalibration affects scoring)
        self.vector_store = PlaybookVectorStore(config)
        self.graph_builder = BoundedGraphBuilder(config, self.vector_store)
        self.cr_scorer = ContextualRelevanceScorer(config)
        self.causal_scorer = CompositeCausalScorer(config, self.cr_scorer)

        # Stage 5 & 6
        self.layers_store = PrescriptiveLayersStore()
        self.supervisor = SupervisorFramework(self.layers_store, config)
        self.web_tools = WebIntelligenceTools()

        # Stage 7
        self.rca_corrector = RCACorrectionManager(self.cr_scorer, config)
        self.trust_tuner = ModelTrustTuner(self.supervisor.swarm, config)
        self.playbook_appender = DynamicPlaybookAppender(self.layers_store)
        self.demoted_nodes: Dict[str, Set[str]] = {}
        self.verified_drivers: Dict[str, CandidateNode] = {}
        self.rejected_actions: Dict[str, List[str]] = {}
        self.learning_version = 0

        # Stage 0 -> global ML model (batch): reconcile 4 sources, train on history, keep anomaly day for SHAP
        raw_web, raw_it, raw_sales, raw_market, _ = self.data_generator.generate_raw_sources()
        self.model_frame = HeterogeneousDataReconciler().reconcile(raw_web, raw_it, raw_sales, raw_market)
        self.global_model = GlobalKPIModel()
        self.global_model.train_global_model(self.model_frame)
        self.anomaly_row = self.model_frame.iloc[[-1]]

    # ================================================================== Stage 1
    def scan_fleet(self) -> List[AnchorNode]:
        return self.detector.scan_fleet(self.contracts, self.telemetry_series)

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        if scenario_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario_id}'. Options: {list(SCENARIOS)}")
        return SCENARIOS[scenario_id](self.base_time)

    def detect_anchor(self, scenario: Dict[str, Any]):
        """Runs the Stage-1 detector on the scenario's raw telemetry. Returns (anchor | None, report)."""
        reference: AnchorNode = scenario["anchor"]
        history = scenario.get("history")
        observation = scenario.get("observation")
        contract = self.contracts.get(reference.kpi_id)
        if not history or observation is None or contract is None:
            return reference, {"mode": "precomputed", "note": "No raw telemetry for this scenario; using reference anchor."}

        surrogate = self.telemetry_series.get(scenario.get("surrogate_kpi_id") or contract.surrogate_reference or "", None)
        is_anomaly, anchor = self.detector.evaluate_metric(
            contract, history, observation, surrogate, extra_dimensions=reference.dimensions)
        report = {
            "mode": "detected",
            "contract": contract.kpi_id,
            "lifecycle_stage": contract.lifecycle_stage.value,
            "history_points": len(history),
            "surrogate_kpi": scenario.get("surrogate_kpi_id") if surrogate else None,
            "is_anomaly": is_anomaly,
        }
        if anchor is not None:
            anchor.metric_name = reference.metric_name
            report.update({"z_score": anchor.z_score, "baseline_mean": anchor.baseline_mean,
                           "baseline_std": anchor.baseline_std, "trigger_rule": anchor.trigger_rule})
        return (anchor if is_anomaly else None), report

    # ================================================================== main run
    def _cache_key(self, scenario_id, user_role, primary_llm, bluesky_llm, override_driver, extra_context) -> str:
        parts = [scenario_id, user_role.value, primary_llm, bluesky_llm,
                 override_driver.node_id if override_driver else "-",
                 sorted((extra_context or {}).get("rejected_actions", [])), self.learning_version]
        return "|".join(str(p) for p in parts)

    def run_pipeline(
        self,
        scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        force_refresh: bool = False,
        primary_llm: str = "mock",
        bluesky_llm: str = "mock",
        enable_super_anchor: bool = True,
        override_driver: Optional[CandidateNode] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        use_learned_overrides: bool = True,
    ) -> Dict[str, Any]:
        start = time.time()
        primary_llm, bluesky_llm = (primary_llm or "mock").lower(), (bluesky_llm or "mock").lower()
        assert_providers_allowed(user_role, primary_llm, bluesky_llm)  # server-side RBAC

        scenario = self.load_scenario(scenario_id)
        kpi_id = scenario["anchor"].kpi_id
        if override_driver is None and use_learned_overrides:
            override_driver = self.verified_drivers.get(kpi_id)

        cache_key = self._cache_key(scenario_id, user_role, primary_llm, bluesky_llm, override_driver, extra_context)
        if not force_refresh:
            cached = self.supervisor.cache_get(cache_key)
            if cached is not None:
                result = cached["result"]
                mp: UnifiedMasterPayload = result.get("master_payload")
                if mp is not None:
                    mp.runtime_metadata.cache_hit = True
                    mp.runtime_metadata.execution_latency_ms = int((time.time() - start) * 1000)
                    mp.runtime_metadata.total_tokens_consumed = 0
                    mp.runtime_metadata.estimated_cost_usd = 0.0
                result["cache_hit"] = True
                return result

        # ---------------- Stage 1: detection ----------------
        anchor, detection = self.detect_anchor(scenario)
        if anchor is None:
            return {"status": "NO_ANOMALY", "reason": "Stage-1 detector did not confirm an anomaly.",
                    "detection": detection, "anchor": scenario["anchor"], "master_payload": None, "dag_payload": None}

        evidence_pool: List[CandidateNode] = scenario["evidence_pool"]
        context: Dict[str, Any] = dict(scenario.get("context", {}))
        context.update(copy.deepcopy(extra_context or {}))
        rejected = list(dict.fromkeys(self.rejected_actions.get(kpi_id, []) + context.get("rejected_actions", [])))
        context["rejected_actions"] = rejected
        context["force_refresh"] = force_refresh

        if enable_super_anchor and context.get("concurrent_alerts"):
            concurrent = context["concurrent_alerts"]
            anchor.metric_name = f"SUPER_ANCHOR: {anchor.metric_name} + {len(concurrent)} others"
            anchor.dimensions["clustered_kpis"] = ", ".join(concurrent)
            anchor.trigger_rule = "TEMPORAL_COMPOUND_ANOMALY"
            context["super_anchor_applied"] = True

        # ---------------- Stage 2: scoping + security ----------------
        scoped = self.scoper.filter_by_direction(anchor, evidence_pool, context)
        scoped_out = [n for n in evidence_pool if n.node_id not in {s.node_id for s in scoped}]
        cleared, security_audit = self.security_matrix.apply_security_governance(scoped, user_role)
        if security_audit.get("abstain_recommended"):
            return {"status": "ABSTAINED", "reason": security_audit["abstain_reason"], "security_audit": security_audit,
                    "anchor": anchor, "detection": detection, "dag_payload": None, "master_payload": None}

        # ---------------- Stage 3 & 4: cage, scoring, brakes ----------------
        caged = self.graph_builder.apply_deterministic_pre_pruning(anchor, cleared)
        cage_report = dict(self.graph_builder.last_cage_report)
        scored = self.causal_scorer.score_candidate_nodes(
            anchor, caged, context, global_model=self.global_model, anomaly_row=self.anomaly_row,
            demoted_node_ids=self.demoted_nodes.get(kpi_id, set()))
        dag, dag_payload, surviving, discarded, history_nodes = self.graph_builder.build_bounded_dag(anchor, scored)
        score_by_id = {t[0].node_id: t for t in scored}

        # Primary driver selection
        confidence = "HIGH"
        if override_driver is not None:
            ov = override_driver.model_copy(deep=True)
            if ov.node_id not in dag.graph:
                dag.add_node(ov.node_id, title=ov.title, node_type=ov.node_type.value, content=ov.content,
                             is_masked=ov.is_masked, dimensions=ov.dimensions, hop=1)
                dag.add_edge(ov.node_id, anchor.kpi_id, weight=1.0, contextual_relevance=1.0, causal_impact=1.0,
                             tier="Human-verified (analyst override)", relation="human_verified", hop=1, path_weight=1.0)
            surviving = [ov] + [n for n in surviving if n.node_id != ov.node_id]
            discarded = [n for n in discarded if n.node_id != ov.node_id]
            scored = [(ov, 1.0, 1.0, 1.0, "Human-verified (analyst override)", {"human_verified": True})] + \
                     [t for t in scored if t[0].node_id != ov.node_id]
            score_by_id[ov.node_id] = scored[0]
            dag_payload = dag.to_payload(anchor.kpi_id, dag_payload.pruned_edges_count,
                                         self.config.max_traversal_hops, self.config.edge_prune_weight_threshold)
            primary_driver, confidence = ov, "HUMAN_VERIFIED"
        elif surviving:
            primary_driver = surviving[0]
        else:
            real = [t for t in scored if not is_historical(t[0]) and t[1] > 0]
            primary_driver = real[0][0] if real else None
            confidence = "LOW" if real else "NONE"
        primary_w = score_by_id[primary_driver.node_id][1] if primary_driver is not None else 0.0

        # Noise-signature check (institutional memory)
        noise_verdict = None
        for h in history_nodes:
            if h.node_type != CandidateNodeType.HISTORICAL_NOISE:
                continue
            sim = float(h.metadata.get("similarity_score", 0.0))
            # An analyst flagged this exact KPI's signature as noise -> suppress on any retrieval hit;
            # a generic noise signature suppresses only when it is very similar and outweighs the evidence.
            human_flag = bool(h.metadata.get("human_flagged")) and h.metadata.get("kpi_id") == kpi_id
            if human_flag or (sim >= self.config.noise_suppression_similarity
                              and (confidence in ("LOW", "NONE") or sim > primary_w)):
                noise_verdict = {"historical_id": h.metadata.get("historical_id"), "similarity": sim,
                                 "content": h.content, "human_flagged": human_flag}
                break

        # ---------------- context for the swarm ----------------
        context["financial_impact_usd"] = context.get("financial_impact_usd", abs(anchor.variance_pct) * 3500.0)
        context["ruled_out_titles"] = [f"{n.title} (W={score_by_id[n.node_id][1]:.2f})" for n in discarded] + \
                                      [f"{r['title']} ({r['reason']})" for r in cage_report.get("rejected", [])] + \
                                      [f"{n.title} (outside {context.get('scope_direction', 'search')} scope)" for n in scoped_out]
        for t in scored:
            if t[4].startswith("Tier 1 (Gold) — Multivariate DAG"):
                context["metric_tree_math"] = {k: v for k, v in t[5].items() if k.endswith("_usd")}
                break
        if web_intelligence_enabled():
            ambient = [n for n in surviving if n.node_type in (CandidateNodeType.COMPETITOR_ACTION, CandidateNodeType.MACRO_INDICATOR)]
            if ambient:
                context["external_intelligence"] = self.web_tools.run_external_evaluation(
                    ambient[0].content, context.get("market_ticker", "XRT"))

        evidence_nodes, budget_pruned = self.supervisor.check_token_budget_governor(surviving)
        external = is_public_provider(primary_llm) or is_public_provider(bluesky_llm)
        llm_nodes = self.security_matrix.mask_for_external_llm(evidence_nodes) if external else evidence_nodes
        sec_label = "TIER_2_TOKEN_MASKING" if any(n.is_masked for n in llm_nodes) else "PUBLIC_UNRESTRICTED"
        if security_audit.get("pruned_nodes_count"):
            sec_label = "TIER_1_DOMAIN_PRUNING + " + sec_label

        def edge_info(n):
            for _, _, d in dag.graph.out_edges(n.node_id, data=True):
                return d.get("hop", 1), d.get("relation", "causes")
            return 1, "causes"

        evidence_dicts = []
        for n in llm_nodes:
            t = score_by_id.get(n.node_id)
            hop, rel = edge_info(n)
            evidence_dicts.append({"node_id": n.node_id, "title": n.title, "content": n.content,
                                   "node_type": n.node_type.value, "causal_weight": t[1] if t else 0.0,
                                   "tier": t[4] if t else "", "hop": hop, "relation": rel, "is_masked": n.is_masked})
        history_dicts = [{"node_id": h.node_id, "title": h.title, "content": h.content, "node_type": h.node_type.value,
                          "historical_id": h.metadata.get("historical_id"),
                          "similarity": h.metadata.get("similarity_score", 0.0)} for h in history_nodes]
        anchor_dict = anchor.model_dump(mode="json")

        # ---------------- Stage 5 & 6: governed swarm ----------------
        if noise_verdict:
            final_state = self._noise_state(anchor, noise_verdict, evidence_dicts, history_dicts, context)
        else:
            final_state = self.supervisor.orchestrator.execute(
                anchor_dict, evidence_dicts, context, historical_context=history_dicts,
                user_role=user_role.value, primary_llm=primary_llm, bluesky_llm=bluesky_llm)

        master_payload = self._assemble_payload(
            anchor, primary_driver, primary_w, confidence, sec_label, surviving, discarded, scored,
            final_state, context, primary_llm, budget_pruned, start)

        result = {
            "status": "SUCCESS",
            "scenario_id": scenario_id,
            "scenario_title": scenario.get("title"),
            "anchor": anchor,
            "detection": detection,
            "dag": dag,
            "dag_payload": dag_payload,
            "primary_driver": primary_driver,
            "surviving_evidence": surviving,
            "discarded_noise": discarded,
            "historical_context": history_nodes,
            "scored_nodes": scored,
            "cage_report": cage_report,
            "scoped_out": [n.node_id for n in scoped_out],
            "noise_verdict": noise_verdict,
            "master_payload": master_payload,
            "raw_state": final_state,
            "security_audit": security_audit,
            "context": context,
            "cache_hit": False,
        }
        self.supervisor.cache_put(cache_key, kpi_id, result)
        return result

    # ------------------------------------------------------------------ helpers
    def _noise_state(self, anchor, noise, evidence, history, context) -> Dict[str, Any]:
        action = {
            "action_id": "ACT-NOISE-SUPPRESS", "source_layer": "Institutional Memory - Noise Signature",
            "action": f"Suppress alert: matches known false-alarm signature {noise['historical_id']} "
                      f"(similarity {noise['similarity']:.2f}); keep monitoring, no engineering escalation",
            "estimated_cost_usd": 0.0, "time_to_impact_minutes": 0, "raci_owner": "KPI Owner",
            "approval_status": "AUTO_APPROVED", "critic_verdict": "PASS - zero-cost suppression of a known noise signature.",
            "supervisor_verdict": "APPROVED - noise signature", "model_confidence_weight": round(noise["similarity"], 4),
            "agent_key": "tech_agent", "technical_command": None, "target_environment": None, "status": "APPROVED",
        }
        from kpi_engine.suggester.llm_swarm import build_narrative_template
        story = build_narrative_template(anchor.model_dump(mode="json"), evidence, history, context)
        return {"approved_proposals": [action], "rejected_proposals": [], "proposals": [action],
                "blue_sky_proposals": [], "blue_sky_critique": "Not run: alert suppressed as known noise.",
                "narrative": f"FALSE-ALARM CHECK: this movement matches a known noise signature ({noise['content']}) " + story,
                "narrative_source": "Deterministic template (noise suppression)", "final_status": "NOISE_SUPPRESSED",
                "iteration_count": 0, "supervisor_feedback": "Suppressed by institutional memory noise signature.",
                "tokens_input": 0, "tokens_output": 0, "cache_hits": 0, "llm_errors": [], "orchestration_mode": "n/a"}

    def _assemble_payload(self, anchor, primary_driver, primary_w, confidence, sec_label, surviving, discarded,
                          scored, final_state, context, primary_llm, budget_pruned, start) -> UnifiedMasterPayload:
        swarm = self.supervisor.swarm
        share_by_node = {t[0].node_id: t[5].get("w_cf", t[5].get("explained_share")) for t in scored if len(t) > 5}

        approved = sorted(final_state.get("approved_proposals", []),
                          key=lambda p: (not p.get("is_fallback", False), p.get("model_confidence_weight", 0)),
                          reverse=True)
        approved = [dict(p) for p in approved[: self.config.max_recommended_actions]]
        for p in approved:
            p["explained_share"] = share_by_node.get(p.get("addresses_node_id"))

        exec_view = swarm.generate_executive_view(anchor, primary_driver, approved, context,
                                                  final_state.get("narrative", ""), final_state.get("narrative_source", ""))
        eng_view = swarm.generate_engineer_view(anchor, primary_driver, approved, surviving)
        ops_view = swarm.generate_ops_view(anchor, primary_driver, approved)
        blue_sky = [swarm.to_action_block(p, anchor, requires_shadow_run=True)
                    for p in final_state.get("blue_sky_proposals", [])]

        discarded_blocks = [DiscardedCandidateBlock(action=p.get("action", ""), source_layer=p.get("source_layer", ""),
                                                    critic_verdict=p.get("critic_verdict", "REJECTED"))
                            for p in final_state.get("rejected_proposals", [])]
        score_by_id = {t[0].node_id: t for t in scored}
        discarded_blocks += [DiscardedCandidateBlock(
            action=f"Hypothesis discarded: {n.title}", source_layer="Causal Graph Pruning (The Brakes)",
            critic_verdict=f"REJECTED: W = {score_by_id[n.node_id][1]:.3f} < {self.config.edge_prune_weight_threshold:.2f}")
            for n in discarded]

        tin, tout = int(final_state.get("tokens_input", 0)), int(final_state.get("tokens_output", 0))
        cost = self.supervisor.record_spend(tin, tout)
        runtime = RuntimeMetadataBlock(
            execution_latency_ms=int((time.time() - start) * 1000),
            total_tokens_consumed=tin + tout, input_tokens=tin, output_tokens=tout,
            estimated_cost_usd=round(cost, 6),
            model_routed=f"{primary_llm} (primary) via {final_state.get('orchestration_mode', 'sequential')}",
            orchestration_mode=final_state.get("orchestration_mode", "sequential"),
            swarm_iterations=int(final_state.get("iteration_count", 0)),
            llm_cache_hits=int(final_state.get("cache_hits", 0)),
            budget_pruning_applied=budget_pruned,
            llm_errors=list(final_state.get("llm_errors", [])),
        )
        if primary_driver is not None:
            driver_text = primary_driver.title if primary_driver.is_masked else primary_driver.content
        else:
            driver_text = "Unexplained - no evidence cleared the causal threshold"
        anchor_ref = AnchorReferenceBlock(
            metric=anchor.metric_name, primary_driver=driver_text,
            primary_driver_id=primary_driver.node_id if primary_driver is not None else None,
            causal_weight=round(primary_w, 3), confidence=confidence, security_applied=sec_label)

        status = final_state.get("final_status", "UNKNOWN")
        supervisor_msg = (f"{status} after {final_state.get('iteration_count', 0)} swarm iteration(s) - "
                          f"{final_state.get('supervisor_feedback') or ''}").strip(" -")
        return UnifiedMasterPayload(
            anchor_reference=anchor_ref, executive_view=exec_view, engineer_view=eng_view, ops_view=ops_view,
            blue_sky_actions=blue_sky, discarded_candidates=discarded_blocks, runtime_metadata=runtime,
            supervisor_status=supervisor_msg)

    def _invalidate(self, kpi_id: Optional[str]):
        self.learning_version += 1
        self.supervisor.execute_invalidation_cascade(kpi_id)

    # ================================================================== Stage 7: closed loop
    def handle_human_rca_override(
        self,
        scenario_id: str,
        demoted_node_id: Optional[str],
        promoted_node_id: Optional[str] = None,
        custom_injected_text: Optional[str] = None,
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        primary_llm: str = "mock",
        bluesky_llm: str = "mock",
        is_noise: bool = False,
        analyst_id: str = "analyst",
    ) -> Dict[str, Any]:
        """Human RCA correction -> semantic recalibration -> invalidation cascade -> regenerated payload."""
        scenario = self.load_scenario(scenario_id)
        anchor: AnchorNode = scenario["anchor"]
        pool = {n.node_id: n for n in scenario["evidence_pool"]}
        demoted = pool.get(demoted_node_id) if demoted_node_id else None
        previous = self.verified_drivers.get(anchor.kpi_id)
        if demoted is None and previous is not None and previous.node_id == demoted_node_id:
            demoted = previous
        promoted = pool.get(promoted_node_id) if promoted_node_id else None

        if is_noise:
            direction = "dropped" if anchor.variance_pct < 0 else "spiked"
            text = (f"False Alarm (analyst-flagged): {anchor.metric_name} {direction} "
                    f"{abs(anchor.variance_pct):.0f}% {' '.join(str(v) for v in anchor.dimensions.values())}. "
                    f"{custom_injected_text or 'Confirmed as noise by analyst; no action required.'}")
            self.vector_store.append_incident(text, {
                "id": f"NOISE-HUMAN-{uuid.uuid4().hex[:6]}", "type": "Noise", "impact": "Zero",
                "region": anchor.dimensions.get("region", "Global"), "kpi_id": anchor.kpi_id,
                "human_flagged": True})
            self.verified_drivers.pop(anchor.kpi_id, None)
            self._invalidate(anchor.kpi_id)
            result = self.run_pipeline(scenario_id, user_role, True, primary_llm, bluesky_llm)
            return {"status": "NOISE_FLAGGED_AND_REGENERATED", "verified_driver": None,
                    "recalibration_record": {"noise_injected": True, "text": text},
                    "master_payload": result.get("master_payload"), "result": result}

        verified, record = self.rca_corrector.perform_rca_override(
            anchor_kpi_id=anchor.kpi_id, demoted_driver=demoted, promoted_driver=promoted,
            injected_custom_text=custom_injected_text or (None if promoted else f"Alternative evidence promoted: {promoted_node_id}"),
            analyst_id=analyst_id, anchor_timestamp=anchor.timestamp, anchor_dimensions=anchor.dimensions)
        if demoted is not None:
            self.demoted_nodes.setdefault(anchor.kpi_id, set()).add(demoted.node_id)
        self.verified_drivers[anchor.kpi_id] = verified
        self._invalidate(anchor.kpi_id)

        result = self.run_pipeline(scenario_id, user_role, True, primary_llm, bluesky_llm, override_driver=verified)
        return {"status": "OVERRIDDEN_AND_REGENERATED", "verified_driver": verified, "recalibration_record": record,
                "master_payload": result.get("master_payload"), "result": result}

    def handle_rejected_fix(
        self,
        scenario_id: str,
        primary_driver: Optional[CandidateNode],
        rejected_action_text: str,
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        primary_llm: str = "mock",
        bluesky_llm: str = "mock",
        action_id: Optional[str] = None,
        source_layer: Optional[str] = None,
        user_id: str = "user",
    ) -> Dict[str, Any]:
        """A human denies a fix: remember it, decay the producing agent's trust, regenerate."""
        kpi_id = self.load_scenario(scenario_id)["anchor"].kpi_id
        lst = self.rejected_actions.setdefault(kpi_id, [])
        if rejected_action_text not in lst:
            lst.append(rejected_action_text)
        feedback = None
        if source_layer:
            feedback = self.trust_tuner.record_feedback(action_id or "ACT-UNKNOWN", source_layer, "REJECT", user_id)
        self._invalidate(kpi_id)
        override = primary_driver if (primary_driver is not None and primary_driver.metadata.get("human_verified")) else None
        result = self.run_pipeline(scenario_id, user_role, True, primary_llm, bluesky_llm, override_driver=override)
        return {"status": "FIX_REJECTED_AND_REGENERATED", "verified_driver": result.get("primary_driver"),
                "trust_feedback": feedback, "master_payload": result.get("master_payload"), "result": result}

    def handle_accepted_fix(self, scenario_id: str, action_id: str, source_layer: str, action_text: str,
                            user_id: str = "user", modified_action: Optional[str] = None,
                            modified_command: Optional[str] = None, root_cause_text: Optional[str] = None,
                            target_environment: str = "production") -> Dict[str, Any]:
        """A human approves a fix (optionally modified): boost trust and, if modified, learn a new playbook."""
        signal = "MODIFY" if modified_action else "ACCEPT"
        feedback = self.trust_tuner.record_feedback(action_id, source_layer, signal, user_id)
        playbook = None
        if modified_action:
            playbook = self.playbook_appender.capture_execution_delta(
                base_action_id=action_id, original_action=action_text, modified_action=modified_action,
                modified_command=modified_command or "", engineer_id=user_id,
                target_environment=target_environment, root_cause_text=root_cause_text)
        kpi_id = self.load_scenario(scenario_id)["anchor"].kpi_id
        self._invalidate(None if playbook else kpi_id)
        return {"status": "FEEDBACK_RECORDED", "trust_feedback": feedback, "playbook_entry": playbook}

    def reset_learning(self, scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear human overrides / rejections (all KPIs, or one scenario's KPI)."""
        if scenario_id:
            kpi = self.load_scenario(scenario_id)["anchor"].kpi_id
            for d in (self.demoted_nodes, self.verified_drivers, self.rejected_actions):
                d.pop(kpi, None)
            self._invalidate(kpi)
        else:
            self.demoted_nodes.clear()
            self.verified_drivers.clear()
            self.rejected_actions.clear()
            self._invalidate(None)
        return {"status": "RESET", "scenario_id": scenario_id}
