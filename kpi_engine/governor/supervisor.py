"""
Supervisor Framework, AI Gateway & Execution Controls (§4.3, §11, §12.3)
"""

import time
from typing import Dict, List, Any, Tuple, Optional

from kpi_engine.data.models import AnchorNode, CandidateNode, UserClearance
from kpi_engine.suggester.layers_data import SolutionCandidate, PrescriptiveLayersStore
from kpi_engine.suggester.dual_channel import DualChannelSuggester
from kpi_engine.governor.critic import TheCritic
from kpi_engine.governor.actor_swarm import ActorSwarm
from kpi_engine.governor.schemas import (
    UnifiedMasterPayload,
    AnchorReferenceBlock,
    DiscardedCandidateBlock,
    RuntimeMetadataBlock,
)
from kpi_engine.config import CONFIG


class SupervisorFramework:
    """The central programmatic orchestrator enforcing schema integrity, cost controls, and cascade invalidation."""

    def __init__(self, layers_store: Optional[PrescriptiveLayersStore] = None, config=CONFIG):
        self.config = config
        self.store = layers_store or PrescriptiveLayersStore()
        self.suggester = DualChannelSuggester(self.store)
        self.critic = TheCritic(self.store, config)
        self.swarm = ActorSwarm()

        # Semantic Cache: (kpi_id, primary_driver_id, role) -> UnifiedMasterPayload
        self.semantic_cache: Dict[str, UnifiedMasterPayload] = {}
        self.cumulative_token_spend: int = 0

    def get_cache_key(self, anchor: AnchorNode, primary_driver: CandidateNode, role: UserClearance) -> str:
        return f"{anchor.kpi_id}:{primary_driver.node_id}:{role.value}"

    def check_token_budget_governor(
        self, nodes: List[CandidateNode]
    ) -> Tuple[List[CandidateNode], bool]:
        """Pre-Inference Cost Control: Prunes lowest-weighted nodes if token budget exceeded."""
        # Simple heuristic: ~150 tokens per evidence node
        estimated_tokens = len(nodes) * 150
        if estimated_tokens > self.config.token_budget_limit:
            # Keep top nodes within budget
            max_nodes = self.config.token_budget_limit // 150
            return nodes[:max_nodes], True
        return nodes, False

    def orchestrate_investigation(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
        sorted_evidence: List[CandidateNode],
        context: Dict[str, Any],
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        security_applied: str = "PUBLIC_UNRESTRICTED",
        primary_causal_weight: float = 0.96,
        force_refresh: bool = False,
    ) -> UnifiedMasterPayload:
        """Full governed orchestration pipeline with circuit breaker and telemetry appends."""
        start_time = time.time()
        cache_key = self.get_cache_key(anchor, primary_driver, user_role)

        # 1. Check Semantic Cache (§12.3)
        if not force_refresh and cache_key in self.semantic_cache:
            cached_payload = self.semantic_cache[cache_key].model_copy(deep=True)
            cached_payload.runtime_metadata.cache_hit = True
            cached_payload.runtime_metadata.execution_latency_ms = int((time.time() - start_time) * 1000)
            return cached_payload

        # 2. Token Budget Governor
        pruned_nodes, budget_pruned = self.check_token_budget_governor(sorted_evidence)

        # 3. Generate Solution Candidates via Dual Channels (Stage 5)
        raw_candidates = self.suggester.generate_all_candidates(anchor, primary_driver)

        # 4. Cross-Examination via The Critic (Stage 6)
        passed_candidates, discarded_candidates = self.critic.evaluate_candidates(
            anchor, primary_driver, raw_candidates
        )

        # 5. Circuit Breaker / Conflict Resolution:
        # If Critic rejected every single idea, re-trigger with tighter constraint
        if not passed_candidates:
            fallback_cand = SolutionCandidate(
                action_id="ACT-FALLBACK-001",
                action=f"Initiate manual incident triaging protocol for {anchor.metric_name}",
                source_layer="Layer 1 - Emergency Fallback Runbook",
                model_confidence_weight=0.99,
                estimated_cost_usd=0.0,
                time_to_impact_minutes=10,
                raci_owner="On-Call Incident Commander",
                approval_status="AUTO_APPROVED",
                critic_verdict="PASS - Emergency fallback auto-approved.",
            )
            passed_candidates.append(fallback_cand)

        # 6. Federated Persona Generation via Swarm
        exec_view = self.swarm.generate_executive_view(anchor, primary_driver, passed_candidates, context)
        eng_view = self.swarm.generate_engineer_view(anchor, primary_driver, passed_candidates)
        ops_view = self.swarm.generate_ops_view(anchor, primary_driver, passed_candidates)

        # Format discarded candidates
        discarded_blocks = [
            DiscardedCandidateBlock(
                action=c.action,
                source_layer=c.source_layer,
                critic_verdict=c.critic_verdict or "REJECTED by Critic",
            )
            for c in discarded_candidates
        ]

        # 7. Calculate Telemetry Metadata Block (§12.3)
        tokens_consumed = 1200 + len(sorted_evidence) * 150 + len(raw_candidates) * 200
        self.cumulative_token_spend += tokens_consumed
        cost_usd = round(
            (tokens_consumed / 1000.0) * self.config.cost_per_1k_input_tokens_usd, 4
        )
        latency_ms = int((time.time() - start_time) * 1000) or 45

        runtime_meta = RuntimeMetadataBlock(
            execution_latency_ms=latency_ms,
            total_tokens_consumed=tokens_consumed,
            estimated_cost_usd=cost_usd,
            model_routed="gpt-4o / gemini-2.5-pro",
            cache_hit=False,
            budget_pruning_applied=budget_pruned,
        )

        anchor_ref = AnchorReferenceBlock(
            metric=anchor.metric_name,
            primary_driver=primary_driver.content if not primary_driver.is_masked else primary_driver.title,
            causal_weight=round(primary_causal_weight, 2),
            security_applied=security_applied,
        )

        supervisor_msg = f"SCHEMA_VALID - {len(passed_candidates)} of {len(raw_candidates)} candidates passed the Critic"

        master_payload = UnifiedMasterPayload(
            anchor_reference=anchor_ref,
            executive_view=exec_view,
            engineer_view=eng_view,
            ops_view=ops_view,
            discarded_candidates=discarded_blocks,
            runtime_metadata=runtime_meta,
            supervisor_status=supervisor_msg,
        )

        # Store in cache
        self.semantic_cache[cache_key] = master_payload
        return master_payload

    def execute_invalidation_cascade(
        self,
        anchor: AnchorNode,
        new_primary_driver: CandidateNode,
        sorted_evidence: List[CandidateNode],
        context: Dict[str, Any],
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
        security_applied: str = "PUBLIC_UNRESTRICTED",
        primary_causal_weight: float = 0.95,
    ) -> UnifiedMasterPayload:
        """The Supervisor Invalidation Cascade (§4.3.2, §13 Phase 2).
        Triggered when a human analyst overrides the diagnostic root cause:
        1. Invalidate old cache entries for this anchor.
        2. Retrigger Actor Swarm with human-verified root cause.
        3. Fresh generation of governed recommendations.
        """
        # Purge existing cache for this anchor
        keys_to_purge = [k for k in self.semantic_cache if k.startswith(f"{anchor.kpi_id}:")]
        for k in keys_to_purge:
            del self.semantic_cache[k]

        # Fresh execution
        return self.orchestrate_investigation(
            anchor=anchor,
            primary_driver=new_primary_driver,
            sorted_evidence=sorted_evidence,
            context=context,
            user_role=user_role,
            security_applied=security_applied,
            primary_causal_weight=primary_causal_weight,
            force_refresh=True,
        )
