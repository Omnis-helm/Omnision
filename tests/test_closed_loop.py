"""
Test Suite for Closed-Loop Continuous Learning (§4.1.2, §4.3.2, §13)
"""

import random

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance

S1 = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"


def test_full_pipeline_scenario_1_stripe():
    engine = KPIStorytellingEngine()
    result = engine.run_pipeline(S1, UserClearance.EXECUTIVE_VP)

    assert result["status"] == "SUCCESS"
    assert result["anchor"].kpi_id == "KPI_WEST_CHECKOUT_CONV"
    assert result["detection"]["mode"] == "detected" and abs(result["anchor"].z_score - 5.19) < 0.01

    master = result["master_payload"]
    assert "Stripe v4.1" in master.anchor_reference.primary_driver
    assert master.anchor_reference.primary_driver_id == "NODE-SYS-101"
    assert master.executive_view.financial_impact_usd == 42000.0
    assert master.executive_view.business_risk_level == "HIGH"
    assert "Roll back Stripe" in master.executive_view.recommended_actions[0].action
    assert all(a.approval_status != "DISCARDED" for a in master.executive_view.recommended_actions)
    assert "Stripe" in master.executive_view.narrative

    assert "8000ms latency" in master.engineer_view.technical_root_cause
    assert "helm rollback" in master.engineer_view.execution_playbook.command
    assert any("REJECTED" in d.critic_verdict for d in master.discarded_candidates)

    # mock provider -> no LLM tokens are invented
    assert master.runtime_metadata.total_tokens_consumed == 0
    # second call is a semantic cache hit
    assert engine.run_pipeline(S1, UserClearance.EXECUTIVE_VP)["cache_hit"] is True


def test_closed_loop_rca_override_cascade():
    engine = KPIStorytellingEngine()
    engine.run_pipeline(S1)

    override_res = engine.handle_human_rca_override(
        scenario_id=S1,
        demoted_node_id="NODE-SYS-101",
        custom_injected_text="Critical database deadlocks on postgres checkout_sessions table",
    )
    assert override_res["status"] == "OVERRIDDEN_AND_REGENERATED"
    assert "database deadlocks" in override_res["verified_driver"].content
    rec = override_res["recalibration_record"]
    assert rec["new_semantic_threshold"] < rec["previous_semantic_threshold"]
    assert override_res["master_payload"].anchor_reference.confidence == "HUMAN_VERIFIED"

    # The override persists (institutional memory) until reset, and the demoted node is penalised
    again = engine.run_pipeline(S1)
    assert "database deadlocks" in again["master_payload"].anchor_reference.primary_driver
    assert "NODE-SYS-101" in engine.demoted_nodes["KPI_WEST_CHECKOUT_CONV"]
    engine.reset_learning(S1)
    assert engine.run_pipeline(S1)["master_payload"].anchor_reference.primary_driver_id == "NODE-SYS-101"


def test_closed_loop_model_trust_tuning():
    engine = KPIStorytellingEngine()
    engine.trust_tuner.rng = random.Random(1)  # deterministic: no epsilon-greedy shield on this draw
    initial_w = engine.supervisor.swarm.model_weights["challenger_agent"]

    engine.trust_tuner.record_feedback("ACT-CHAL-501", "Layer 5 - Blue-Sky Challenger", "REJECT")
    decayed_w = engine.supervisor.swarm.model_weights["challenger_agent"]
    assert decayed_w == round(initial_w * (1.0 - engine.config.model_penalty_decay_rate), 4)

    tech_initial = engine.supervisor.swarm.model_weights["tech_agent"]
    engine.trust_tuner.record_feedback("ACT-PM-2291", "Layer 1 - Internal Playbook", "ACCEPT")
    assert engine.supervisor.swarm.model_weights["tech_agent"] > tech_initial


def test_rejected_fix_regenerates_a_different_fix_and_decays_trust():
    engine = KPIStorytellingEngine()
    first = engine.run_pipeline(S1)["master_payload"].executive_view.recommended_actions[0]
    tech_before = engine.supervisor.swarm.model_weights["tech_agent"]

    res = engine.handle_rejected_fix(S1, None, first.action, action_id=first.action_id, source_layer=first.source_layer)
    new_actions = [a.action for a in res["master_payload"].executive_view.recommended_actions]
    assert first.action not in new_actions and new_actions
    assert engine.supervisor.swarm.model_weights["tech_agent"] < tech_before


def test_closed_loop_dynamic_playbook_append_is_used_next_run():
    engine = KPIStorytellingEngine()
    initial_pb_count = len(engine.layers_store.layer_1_playbooks)

    out = engine.handle_accepted_fix(
        S1, "ACT-PM-2291", "Layer 1 - Internal Playbook (PM-2291)", "Roll back Stripe v4.1 gateway integration",
        modified_action="Roll back Stripe v4.1 gateway integration AND flush Redis session cache",
        modified_command="helm rollback stripe-gateway 4.0 && redis-cli -n 3 FLUSHDB",
        root_cause_text="Payment Gateway API Timeout (Stripe v4.1), 8000ms latency on POST /v1/charges",
    )
    assert len(engine.layers_store.layer_1_playbooks) == initial_pb_count + 1
    assert out["playbook_entry"]["required_lever"] == "helm_rollback_capability"

    actions = [a.action for a in engine.run_pipeline(S1)["master_payload"].executive_view.recommended_actions]
    assert any("flush Redis" in a for a in actions)


def test_analyst_noise_flag_suppresses_future_alerts():
    engine = KPIStorytellingEngine()
    res = engine.handle_human_rca_override(S1, "NODE-SYS-101", is_noise=True,
                                           custom_injected_text="Known payday traffic pattern")
    assert res["status"] == "NOISE_FLAGGED_AND_REGENERATED"
    master = res["master_payload"]
    assert master.supervisor_status.startswith("NOISE_SUPPRESSED")
    assert master.executive_view.recommended_actions[0].action.startswith("Suppress alert")
