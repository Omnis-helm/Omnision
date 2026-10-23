"""
End-to-end expectations for the four benchmark scenarios (mock provider, deterministic).
"""
import pytest

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance

EXPECTED = {
    "SCENARIO_1_STRIPE_GATEWAY_OUTAGE": ("NODE-SYS-101", "ACT-PM-2291", "Z_SCORE_ANOMALY"),
    "SCENARIO_2_MULTIVARIATE_DAG_SHAP": ("NODE-PRC-201", "ACT-PB-PRICE-17", "Z_SCORE_ANOMALY"),
    "SCENARIO_3_COLD_START_PHASED_HANDOVER": ("NODE-COLD-301", "ACT-PB-MOB-311", "COLD_START_TRIPWIRE"),
    "SCENARIO_4_SECURITY_CLEARANCE_MATRIX": ("NODE-SEC-401", "ACT-FIN-ACC-07", "Z_SCORE_ANOMALY"),
}


@pytest.fixture(scope="module")
def engine():
    return KPIStorytellingEngine()


@pytest.mark.parametrize("scenario_id", list(EXPECTED))
def test_scenario_end_to_end(engine, scenario_id):
    driver_id, action_id, rule = EXPECTED[scenario_id]
    res = engine.run_pipeline(scenario_id, UserClearance.EXECUTIVE_VP, force_refresh=True)
    assert res["status"] == "SUCCESS"
    master = res["master_payload"]

    assert res["anchor"].trigger_rule == rule
    assert master.anchor_reference.primary_driver_id == driver_id
    assert not master.anchor_reference.primary_driver_id.startswith("MEM-")   # memory never becomes the root cause
    assert master.executive_view.recommended_actions[0].action_id == action_id
    for a in master.executive_view.recommended_actions:
        assert a.approval_status in ("AUTO_APPROVED", "PENDING_DIRECTOR_APPROVAL", "PENDING_VP_APPROVAL")
        assert a.supervisor_verdict.startswith("APPROVED")
    assert res["dag_payload"].is_acyclic
    assert all(e.hop <= engine.config.max_traversal_hops for e in res["dag_payload"].edges)
    assert master.blue_sky_actions and master.blue_sky_actions[0].requires_shadow_run
    assert master.executive_view.narrative


def test_scenario_2_two_hop_graph_and_shap(engine):
    res = engine.run_pipeline("SCENARIO_2_MULTIVARIATE_DAG_SHAP", force_refresh=True)
    edges = {(e.source, e.target, e.hop) for e in res["dag_payload"].edges}
    assert ("NODE-COMP-203", "NODE-VOL-202", 2) in edges          # competitor -> volume -> revenue
    assert res["context"]["metric_tree_math"]["total_delta_r_usd"] == pytest.approx(-48000.8, abs=1)
    assert res["context"]["shap_attribution"]["relative_attribution"]["competitor_price"] < 0
