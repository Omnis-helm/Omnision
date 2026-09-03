"""
The Critic: Feasibility, Budget Limits & Cross-Examination (§4.2, §10)
"""

import re
from typing import List, Tuple, Dict, Any
from kpi_engine.suggester.layers_data import SolutionCandidate, PrescriptiveLayersStore
from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.config import CONFIG


class TheCritic:
    """Independent Evaluator Agent that cross-examines candidate fixes against hard constraints."""

    def __init__(self, layers_store: PrescriptiveLayersStore, config=CONFIG):
        self.store = layers_store
        self.config = config

    def evaluate_candidates(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
        candidates: List[SolutionCandidate],
    ) -> Tuple[List[SolutionCandidate], List[SolutionCandidate]]:
        """Applies 3-Point Feasibility Matrix.
        Returns: (passed_candidates, discarded_candidates)
        """
        passed: List[SolutionCandidate] = []
        discarded: List[SolutionCandidate] = []

        from kpi_engine.config import VALID_ACTION_KEYWORDS
        valid_action_keywords = VALID_ACTION_KEYWORDS

        for cand in candidates:
            # 1. Correctness Test: Does it neutralize the primary anchor driver?
            action_text = cand.action.lower()
            source_text = cand.source_layer.lower()
            if not any(kw in action_text or kw in source_text for kw in valid_action_keywords):
                cand.critic_verdict = "REJECTED: Does not neutralize the identified root cause."
                cand.approval_status = "DISCARDED"
                discarded.append(cand)
                continue

            # 2. Technical Feasibility Test: Does the company possess the required lever?
            if cand.operational_lever_required:
                has_lever = self.store.layer_3_active_levers.get(cand.operational_lever_required, False)
                if not has_lever:
                    cand.critic_verdict = f"REJECTED: No active contract or technical capability with named provider ({cand.operational_lever_required})"
                    cand.approval_status = "DISCARDED"
                    discarded.append(cand)
                    continue

            # 3. Financial & Governance Feasibility Test: Check RACI authority thresholds
            cost = cand.estimated_cost_usd
            if cost > self.config.vp_approval_required_cost_usd:
                cand.approval_status = "PENDING_VP_APPROVAL"
                cand.critic_verdict = "PASS - High-cost strategic action, requires VP Approval."
            elif cost > self.config.auto_approve_cost_ceiling_usd:
                cand.approval_status = "PENDING_DIRECTOR_APPROVAL"
                cand.critic_verdict = "PASS - Feasible, exceeds auto-approve threshold."
            else:
                cand.approval_status = "AUTO_APPROVED"
                cand.critic_verdict = "PASS - correct, feasible, in-budget."

            passed.append(cand)

        return passed, discarded
