"""
Test Suite for Closed-Loop Continuous Learning (§4.1.2, §4.3.2, §13)
"""

import pytest
from datetime import datetime, timedelta

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance


def test_full_pipeline_scenario_1_stripe():
    """Verify end-to-end execution of Scenario 1 (Stripe Gateway Outage)."""
    engine = KPIStorytellingEngine()
    result = engine.run_pipeline("SCENARIO_1_STRIPE_GATEWAY_OUTAGE", UserClearance.EXECUTIVE_VP)

    assert result["status"] == "SUCCESS"
    assert result["anchor"].kpi_id == "KPI_WEST_CHECKOUT_CONV"

    master = result["master_payload"]
    assert master.anchor_reference.metric == "West Region Checkout Conversion Rate"
    assert "Stripe v4.1" in master.anchor_reference.primary_driver
    assert master.executive_view.financial_impact_usd == 42000.0
    assert master.executive_view.business_risk_level == "HIGH"
    assert len(master.executive_view.recommended_actions) >= 1
    assert "Roll back Stripe" in master.executive_view.recommended_actions[0].action

    # Engineer View check
    assert "8000ms latency" in master.engineer_view.technical_root_cause
    assert "helm rollback" in master.engineer_view.execution_playbook.command

    # Discarded candidates check
    assert len(master.discarded_candidates) >= 1
    assert "REJECTED" in master.discarded_candidates[0].critic_verdict

    # Runtime Telemetry check
    assert master.runtime_metadata.total_tokens_consumed > 0
    assert master.runtime_metadata.estimated_cost_usd > 0.0


def test_closed_loop_rca_override_cascade():
    """Verify Human RCA Override triggers semantic recalibration and Supervisor Invalidation Cascade."""
    engine = KPIStorytellingEngine()
    # Initial run
    res1 = engine.run_pipeline("SCENARIO_1_STRIPE_GATEWAY_OUTAGE")
    assert res1["status"] == "SUCCESS"

    # Human overrides root cause
    override_res = engine.handle_human_rca_override(
        scenario_id="SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
        demoted_node_id="NODE-SYS-101",
        custom_injected_text="Critical database deadlocks on postgres checkout_sessions table",
    )

    assert override_res["status"] == "OVERRIDDEN_AND_REGENERATED"
    assert "database deadlocks" in override_res["verified_driver"].content
    assert override_res["recalibration_record"]["new_semantic_threshold"] < override_res["recalibration_record"]["previous_semantic_threshold"]


def test_closed_loop_model_trust_tuning():
    """Verify that user REJECT decays model trust W_m and ACCEPT boosts it."""
    engine = KPIStorytellingEngine()
    initial_w = engine.supervisor.swarm.model_weights["challenger_agent"]

    # Reject Challenger action
    log1 = engine.trust_tuner.record_feedback(
        action_id="ACT-CHAL-501",
        source_layer="Layer 5 - Blue-Sky Challenger",
        signal="REJECT",
    )

    decayed_w = engine.supervisor.swarm.model_weights["challenger_agent"]
    assert decayed_w < initial_w
    assert decayed_w == round(initial_w * (1.0 - engine.config.model_penalty_decay_rate), 4)

    # Accept Playbook action
    tech_initial = engine.supervisor.swarm.model_weights["tech_agent"]
    log2 = engine.trust_tuner.record_feedback(
        action_id="ACT-PM-2291",
        source_layer="Layer 1 - Internal Playbook",
        signal="ACCEPT",
    )
    boosted_w = engine.supervisor.swarm.model_weights["tech_agent"]
    assert boosted_w > tech_initial


def test_closed_loop_dynamic_playbook_append():
    """Verify that human modifications to actions are ingested into Layer 1 playbooks."""
    engine = KPIStorytellingEngine()
    initial_pb_count = len(engine.layers_store.layer_1_playbooks)

    new_pb = engine.playbook_appender.capture_execution_delta(
        base_action_id="ACT-101",
        original_action="Roll back Stripe v4.1 gateway integration",
        modified_action="Roll back Stripe v4.1 gateway integration AND flush Redis cache",
        modified_command="helm rollback stripe-gateway 4.0 && redis-cli FLUSHALL",
        engineer_id="engineer_lead_9",
    )

    assert len(engine.layers_store.layer_1_playbooks) == initial_pb_count + 1
    assert "flush Redis cache" in engine.layers_store.layer_1_playbooks[0]["action"]
    assert "redis-cli FLUSHALL" in engine.layers_store.layer_1_playbooks[0]["command"]
