"""
Test Suite for Multi-Agent Swarm, The Critic & RACI Governance (§4.2, §10, §11)
"""

import pytest
from datetime import datetime

from kpi_engine.suggester.layers_data import PrescriptiveLayersStore, SolutionCandidate
from kpi_engine.governor.critic import TheCritic
from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType, LifecycleStage


def test_the_critic_3_point_feasibility_matrix():
    """Verify that the Critic rejects unfeasible levers and flags high-cost fixes for VP approval."""
    store = PrescriptiveLayersStore()
    critic = TheCritic(store)

    base_time = datetime(2026, 8, 30, 10, 0, 0)
    anchor = AnchorNode(
        kpi_id="KPI_WEST_CHECKOUT_CONV",
        metric_name="West Region Checkout Conversion",
        timestamp=base_time,
        current_value=2.80,
        baseline_mean=3.20,
        baseline_std=0.08,
        variance_pct=-12.5,
        z_score=5.0,
        lifecycle_stage=LifecycleStage.MATURE,
        trigger_rule="Z_SCORE_ANOMALY",
    )

    primary_driver = CandidateNode(
        node_id="NODE-SYS-101",
        node_type=CandidateNodeType.SYSTEM_LOG,
        title="Payment Gateway Timeout",
        content="Payment Gateway API Timeout (Stripe v4.1), 8000ms latency",
        timestamp=base_time,
    )

    candidates = [
        # Candidate 1: In-budget feasible action ($0)
        SolutionCandidate(
            action_id="ACT-101",
            action="Roll back Stripe v4.1 gateway integration",
            source_layer="Layer 1 - Internal Playbook",
            estimated_cost_usd=0.0,
            operational_lever_required="helm_rollback_capability",
        ),
        # Candidate 2: High cost action ($125,000) with non-existent lever
        SolutionCandidate(
            action_id="ACT-CHAL-501",
            action="Migrate checkout to alternate cloud provider",
            source_layer="Layer 5 - Blue-Sky Challenger",
            estimated_cost_usd=125000.0,
            operational_lever_required="aws_direct_contract",  # Lever is False in store!
        ),
    ]

    passed, discarded = critic.evaluate_candidates(anchor, primary_driver, candidates)

    assert len(passed) == 1
    assert passed[0].action_id == "ACT-101"
    assert passed[0].approval_status == "AUTO_APPROVED"

    assert len(discarded) == 1
    assert discarded[0].action_id == "ACT-CHAL-501"
    assert discarded[0].approval_status == "DISCARDED"
    assert "No active contract" in discarded[0].critic_verdict
