"""
End-to-End Orchestration Pipeline for the KPI Storytelling Engine (v3.0 / Extended Edition v2.0)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from kpi_engine.data.models import (
    AnchorNode,
    CandidateNode,
    UserClearance,
    SecurityTier,
    LifecycleStage,
)
from kpi_engine.data.generator import KartMitraDataGenerator
from kpi_engine.data.seed_scenarios import (
    get_scenario_1_stripe_outage,
    get_scenario_2_multivariate_price_volume,
    get_scenario_3_cold_start_kpi,
    get_scenario_4_security_clearance,
)
from kpi_engine.detector.anomaly_pipeline import TelemetryAnomalyDetector
from kpi_engine.detector.cold_start import ColdStartAnomalyManager
from kpi_engine.scoper.directional_router import DirectionalScoper
from kpi_engine.scoper.security_matrix import HybridSecurityMatrix
from kpi_engine.graph.bounded_builder import BoundedGraphBuilder
from kpi_engine.causal.composite_scorer import CompositeCausalScorer
from kpi_engine.causal.contextual_relevance import ContextualRelevanceScorer
from kpi_engine.suggester.layers_data import PrescriptiveLayersStore
from kpi_engine.governor.supervisor import SupervisorFramework
from kpi_engine.governor.schemas import UnifiedMasterPayload
from kpi_engine.learning.rca_corrections import RCACorrectionManager
from kpi_engine.learning.trust_tuning import ModelTrustTuner
from kpi_engine.learning.dynamic_playbook import DynamicPlaybookAppender
from kpi_engine.config import CONFIG


class KPIStorytellingEngine:
    """The master pipeline orchestrating all 7 architectural stages."""

    def __init__(self, config=CONFIG):
        self.config = config

        # Stage 0 & 1: Data & Detection
        self.data_generator = KartMitraDataGenerator()
        self.contracts = self.data_generator.generate_contracts()
        self.telemetry_series, self.base_time = self.data_generator.generate_telemetry_series(days=35)
        self.detector = TelemetryAnomalyDetector(config)
        self.cold_start_mgr = ColdStartAnomalyManager(config)

        # Stage 2: Scoping & Security
        self.scoper = DirectionalScoper()
        self.security_matrix = HybridSecurityMatrix()

        # Stage 3 & 4: Graph & Causal Scoring
        self.graph_builder = BoundedGraphBuilder(config)
        self.causal_scorer = CompositeCausalScorer(config)
        self.cr_scorer = ContextualRelevanceScorer(config)

        # Stage 5 & 6: Suggestion, Multi-Agent Swarm, Critic & Supervisor
        self.layers_store = PrescriptiveLayersStore()
        self.supervisor = SupervisorFramework(self.layers_store, config)

        # Stage 7: Closed-Loop Continuous Learning
        self.rca_corrector = RCACorrectionManager(self.cr_scorer, config)
        self.trust_tuner = ModelTrustTuner(self.supervisor.swarm, config)
        self.playbook_appender = DynamicPlaybookAppender(self.layers_store)
        
        # Stage 8: Background ML Model Training (Global Engine)
        from kpi_engine.ml.global_model import GlobalKPIModel
        self.global_model = GlobalKPIModel()
        
        # We simulate the background batch process here
        df, _ = self.data_generator.generate_multivariate_dataframe(days=35)
        self.global_model.train_global_model(df, target_col="kpi_value")
        self.anomaly_row = df.iloc[[-1]] # Keep the last row (anomaly day) for local SHAP later

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Loads one of the four reference benchmark scenarios."""
        if scenario_id == "SCENARIO_1_STRIPE_GATEWAY_OUTAGE":
            return get_scenario_1_stripe_outage(self.base_time)
        elif scenario_id == "SCENARIO_2_MULTIVARIATE_DAG_SHAP":
            return get_scenario_2_multivariate_price_volume(self.base_time)
        elif scenario_id == "SCENARIO_3_COLD_START_PHASED_HANDOVER":
            return get_scenario_3_cold_start_kpi(self.base_time)
        elif scenario_id == "SCENARIO_4_SECURITY_CLEARANCE_MATRIX":
            return get_scenario_4_security_clearance(self.base_time)
        else:
            return get_scenario_1_stripe_outage(self.base_time)

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
    ) -> Dict[str, Any]:
        """Executes the full 7-stage pipeline from detection to governed payload delivery."""
        # 1. Load Scenario / Detect Anchor Node
        scenario = self.load_scenario(scenario_id)
        anchor: AnchorNode = scenario["anchor"]
        evidence_pool: List[CandidateNode] = scenario["evidence_pool"]
        context: Dict[str, Any] = scenario.get("context", {})
        if extra_context:
            context.update(extra_context)

        # --- Simulated Super-Anchor (Alert Storm Deduplication) ---
        if enable_super_anchor and context.get("concurrent_alerts"):
            # Instead of firing 5 parallel Swarms, we merge them into a Compound_Anchor_Node
            concurrent_kpis = context.get("concurrent_alerts", [])
            anchor.metric_name = f"SUPER_ANCHOR: {anchor.metric_name} + {len(concurrent_kpis)} others"
            anchor.dimensions["clustered_kpis"] = ", ".join(concurrent_kpis)
            anchor.trigger_rule = "TEMPORAL_COMPOUND_ANOMALY"
            context["super_anchor_applied"] = True

        # 2. Stage 2: Dynamic Scope Expansion (Directional Scoping)
        scoped_nodes = self.scoper.filter_by_direction(anchor, evidence_pool, context)

        # 3. Stage 2: Hybrid Security Matrix (Tier 1 Pruning vs Tier 2 Masking)
        cleared_nodes, security_audit = self.security_matrix.apply_security_governance(
            scoped_nodes, user_role
        )

        # If Tier 1 Pruning broke the causal math, gracefully abstain
        if security_audit.get("abstain_recommended"):
            return {
                "status": "ABSTAINED",
                "reason": security_audit["abstain_reason"],
                "security_audit": security_audit,
                "anchor": anchor.model_dump(),
                "dag_payload": None,
                "master_payload": None,
            }

        # 4. Stage 3: Bounded Graph Pre-Pruning (The Cage)
        caged_nodes = self.graph_builder.apply_deterministic_pre_pruning(anchor, cleared_nodes)

        # 5. Stage 4: Causal Weighting & Interacting Drivers
        scored_nodes = self.causal_scorer.score_candidate_nodes(
            anchor, 
            caged_nodes, 
            context,
            global_model=self.global_model,
            anomaly_row=self.anomaly_row
        )

        # 6. Stage 3: Traversal Attenuation & DAG Assembly (The Brakes)
        dag_input = [(item[0], item[1], item[2], item[3], item[4]) for item in scored_nodes]
        causal_dag, dag_payload, surviving_evidence, discarded_noise = self.graph_builder.build_bounded_dag(
            anchor, dag_input
        )

        # Determine primary driver and applied security label
        # Filter out Mock FAISS historical nodes to show the actual scenario driver
        real_drivers = [n for n in surviving_evidence if "HIST" not in n.node_id]
        primary_driver = real_drivers[0] if real_drivers else (surviving_evidence[0] if surviving_evidence else caged_nodes[0])
        top_weight = scored_nodes[0][1] if scored_nodes else 0.95

        if override_driver:
            primary_driver = override_driver
            surviving_evidence = [override_driver] + [n for n in surviving_evidence if n.node_id != override_driver.node_id]

        sec_label = "PUBLIC_UNRESTRICTED"
        if any(n.is_masked for n in surviving_evidence):
            sec_label = "TIER_2_TOKEN_MASKING"

        # 7. Stage 5 & 6: Suggestion Network, Multi-Agent Swarm, Critic & Supervisor
        from kpi_engine.governor.langgraph_orchestrator import execute_langgraph_swarm
        from kpi_engine.governor.schemas import UnifiedMasterPayload, AnchorReferenceBlock, RuntimeMetadataBlock
        import time

        start_time = time.time()
        
        # Format inputs for LangGraph
        anchor_dict = anchor.model_dump() if hasattr(anchor, "model_dump") else anchor
        evidence_dicts = [e.model_dump() if hasattr(e, "model_dump") else e for e in surviving_evidence]

        # Execute LangGraph Swarm
        final_state = execute_langgraph_swarm(
            anchor=anchor_dict,
            causal_evidence=evidence_dicts,
            context={**context, 'primary_llm_provider': primary_llm, 'bluesky_llm_provider': bluesky_llm}
        )
        
        # Build the final Master Payload to maintain Streamlit UI compatibility
        approved_proposal = {}
        if final_state.get("proposals"):
            approved_proposal = final_state["proposals"][-1]
            
        latency_ms = int((time.time() - start_time) * 1000)
        tokens = final_state.get("tokens_consumed", 0)
        self.supervisor.cumulative_token_spend += tokens
        cost_usd = round((tokens / 1000.0) * self.config.cost_per_1k_input_tokens_usd, 4)
        
        runtime_meta = RuntimeMetadataBlock(
            execution_latency_ms=latency_ms,
            total_tokens_consumed=tokens,
            estimated_cost_usd=cost_usd,
            model_routed=f"LangGraph - {primary_llm}",
            cache_hit=False,
            budget_pruning_applied=False,
        )

        anchor_ref = AnchorReferenceBlock(
            metric=anchor.metric_name,
            primary_driver=primary_driver.content if not primary_driver.is_masked else primary_driver.title,
            causal_weight=round(top_weight, 2),
            security_applied=sec_label,
        )

        supervisor_msg = f"GRAPH_EXECUTED - Status: {final_state.get('final_status')} (Iter: {final_state.get('iteration_count')})"
        # --- Multi-Action Extraction (Operational & Blue-Sky) ---
        from kpi_engine.governor.schemas import (
            ExecutiveViewBlock, 
            EngineerViewBlock, 
            OpsViewBlock, 
            RecommendedActionBlock,
            ExecutionPlaybookBlock
        )
        
        all_proposals = final_state.get("proposals", [])
        
        recommended_actions_list = []
        
        # Helper to process a proposal
        def process_proposal(prop, is_blue_sky=False):
            raw_action = prop.get("action", "No action returned")
            from kpi_engine.config import FORBIDDEN_ACTION_KEYWORDS
            if any(bad_word in raw_action.lower() for bad_word in FORBIDDEN_ACTION_KEYWORDS):
                return None
                
            est_cost = float(prop.get("estimated_cost_usd", 0.0))
            time_impact = int(prop.get("time_to_impact_minutes", 30))
            
            # Threshold checks
            if est_cost > context.get("vp_approval_required_cost_usd", 5000.0) and not is_blue_sky:
                return None
            if time_impact > 1440 and not is_blue_sky: # Exclude actions taking more than 24 hours unless blue-sky
                return None
                
            # If Blue-Sky, append critique from state
            critique = final_state.get("blue_sky_critique", "Uncritiqued Sandbox Idea.") if is_blue_sky else final_state.get("supervisor_feedback", "N/A")
            
            return RecommendedActionBlock(
                action_id=prop.get("action_id", "ACT-000"),
                action=raw_action,
                estimated_cost_usd=est_cost,
                time_to_impact_minutes=time_impact,
                expected_damage_reverted=f"{abs(anchor.variance_pct):.1f}% KPI Recovery",
                raci_owner=prop.get("raci_owner", "System"),
                approval_status=prop.get("approval_status", "PENDING_REVIEW"),
                source_layer=prop.get("source_layer", "Layer 3"),
                model_confidence_weight=0.95,
                critic_verdict=critique,
                requires_shadow_run=is_blue_sky
            )

        # Process main operational proposals
        for prop in all_proposals:
            action_block = process_proposal(prop, is_blue_sky=False)
            if action_block:
                recommended_actions_list.append(action_block)
                
        # If no valid actions, add a fallback
        if not recommended_actions_list:
            recommended_actions_list.append(RecommendedActionBlock(
                action_id="ACT-ERR-001", action="No valid actions passed security and threshold checks.", estimated_cost_usd=0.0, time_to_impact_minutes=0, expected_damage_reverted="0%", raci_owner="SYSTEM", approval_status="ERROR", source_layer="System", model_confidence_weight=0.0, critic_verdict="All proposals rejected.", requires_shadow_run=False
            ))

        financial_impact = float(context.get("financial_impact_usd", recommended_actions_list[0].estimated_cost_usd * 1.5))
        risk_level = "HIGH" if anchor.z_score >= 5.0 else "MEDIUM"

        exec_view = ExecutiveViewBlock(
            financial_impact_usd=financial_impact,
            business_risk_level=risk_level,
            recommended_actions=recommended_actions_list
        )

        # Make Engineer and Ops Views dynamic based on the actual driver and context
        raw_cause = primary_driver.content if not primary_driver.is_masked else primary_driver.title
        tech_root_cause = f"AI identified {raw_cause} via Swarm" 
        
        target_env = context.get("target_environment", "production-cluster")
        playbook_cmd = f"helm rollback {anchor.dimensions.get('domain', 'service')} --force" if "Stripe" in raw_cause else f"kubectl scale --replicas=5 deployment/{anchor.dimensions.get('category', 'app')}"

        eng_view = EngineerViewBlock(
            technical_root_cause=tech_root_cause,
            system_logs=[f"[WARN] Anomaly in {anchor.metric_name}", f"[INFO] Swarm active on {primary_driver.node_id}"],
            execution_playbook=ExecutionPlaybookBlock(
                command=playbook_cmd,
                target_environment=target_env
            )
        )

        ops_view = OpsViewBlock(
            operational_bottleneck=f"Mitigation required for {anchor.metric_name} variance",
            sla_impact=f"Potential {abs(anchor.variance_pct):.1f}% SLA drop if ignored",
            mitigation_steps=[approved_proposal.get("action", "Manual investigation required")]
        )

        from kpi_engine.governor.schemas import DiscardedCandidateBlock
        discarded_candidate_blocks = [
            DiscardedCandidateBlock(
                action=f"Hypothesis discarded: {n.title}",
                source_layer="Causal Graph Pruning",
                critic_verdict="REJECTED: Signal below causal threshold"
            ) for n in discarded_noise
        ]
        if not discarded_candidate_blocks:
            discarded_candidate_blocks = [
                DiscardedCandidateBlock(
                    action="Hypothesis discarded: Unverified secondary driver",
                    source_layer="Causal Graph Pruning",
                    critic_verdict="REJECTED: Signal below causal threshold"
                )
            ]

        master_payload = UnifiedMasterPayload(
            anchor_reference=anchor_ref,
            executive_view=exec_view,
            engineer_view=eng_view,
            ops_view=ops_view,
            discarded_candidates=discarded_candidate_blocks,
            runtime_metadata=runtime_meta,
            supervisor_status=supervisor_msg,
        )

        return {
            "status": "SUCCESS",
            "anchor": anchor,
            "dag": causal_dag,
            "dag_payload": dag_payload,
            "surviving_evidence": surviving_evidence,
            "discarded_noise": discarded_noise,
            "scored_nodes": scored_nodes,
            "master_payload": master_payload,
            "raw_state": final_state,
            "security_audit": security_audit,
            "context": context,
        }

    def handle_human_rca_override(
        self,
        scenario_id: str,
        demoted_node_id: str,
        promoted_node_id: Optional[str] = None,
        custom_injected_text: Optional[str] = None,
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        primary_llm: str = "mock",
        bluesky_llm: str = "mock",
        is_noise: bool = False,
    ) -> Dict[str, Any]:
        """Closed-loop Phase 1 & 2: Human RCA correction and Supervisor Invalidation Cascade."""
        scenario = self.load_scenario(scenario_id)
        anchor: AnchorNode = scenario["anchor"]
        evidence_pool: List[CandidateNode] = scenario["evidence_pool"]
        context = scenario.get("context", {})

        demoted_node = next((n for n in evidence_pool if n.node_id == demoted_node_id), evidence_pool[0])
        promoted_node = next((n for n in evidence_pool if n.node_id == promoted_node_id), None)

        if promoted_node is None and not custom_injected_text:
            custom_injected_text = f"Alternative evidence promoted: {promoted_node_id or 'Unknown'}"

        verified_driver, recalibration_record = self.rca_corrector.perform_rca_override(
            anchor_kpi_id=anchor.kpi_id,
            demoted_driver=demoted_node,
            promoted_driver=promoted_node,
            injected_custom_text=custom_injected_text,
        )
        
        # 4.5: Continuous Learning - If human flags this signature as Noise, append it to FAISS
        if is_noise:
            import uuid
            self.graph_builder.vector_store.append_incident(
                text=custom_injected_text or f"False Alarm overriding {demoted_node.title}",
                metadata={"id": f"NOISE-{str(uuid.uuid4())[:8]}", "type": "Noise", "impact": "Zero"}
            )
            recalibration_record["noise_injected"] = True

        # Re-trigger with same driver but updated context
        updated_payload = self.run_pipeline(
            scenario_id=scenario_id,
            user_role=user_role,
            force_refresh=True,
            primary_llm=primary_llm,
            bluesky_llm=bluesky_llm,
            override_driver=verified_driver
        )["master_payload"]

        return {
            "status": "OVERRIDDEN_AND_REGENERATED",
            "verified_driver": verified_driver,
            "recalibration_record": recalibration_record,
            "master_payload": updated_payload,
        }

    def handle_rejected_fix(
        self,
        scenario_id: str,
        primary_driver: CandidateNode,
        rejected_action_text: str,
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        primary_llm: str = "mock",
        bluesky_llm: str = "mock",
    ) -> Dict[str, Any]:
        """Triggered when a human explicitly denies a recommended fix."""
        scenario = self.load_scenario(scenario_id)
        anchor: AnchorNode = scenario["anchor"]
        context = scenario.get("context", {})
        
        # Add feedback to context
        if "rejected_actions" not in context:
            context["rejected_actions"] = []
        context["rejected_actions"].append(rejected_action_text)

        # Re-trigger with same driver but updated context
        updated_payload = self.run_pipeline(
            scenario_id=scenario_id,
            user_role=user_role,
            force_refresh=True,
            primary_llm=primary_llm,
            bluesky_llm=bluesky_llm,
            override_driver=primary_driver,
            extra_context={"rejected_actions": context.get("rejected_actions", [])}
        )["master_payload"]

        return {
            "status": "FIX_REJECTED_AND_REGENERATED",
            "verified_driver": primary_driver,
            "master_payload": updated_payload,
        }

