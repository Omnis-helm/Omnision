import pytest
from unittest.mock import patch
from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance

@patch("kpi_engine.suggester.llm_swarm._generate_proposal")
def test_pipeline_rejects_misaligned_action(mock_generate):
    # Mock the LLM to return a completely nonsensical action that has no valid keywords
    # and has terrible semantic similarity to "Stripe Gateway Outage".
    mock_generate.return_value = {
        "action_id": "ACT-GARBAGE-001",
        "action": "Order pizza for the team and paint the office walls blue",
        "source_layer": "Layer 3 - Prescriptive Swarm",
        "estimated_cost_usd": 50.0,
        "time_to_impact_minutes": 60,
        "raci_owner": "HR Team",
        "operational_lever_required": "Pizza_Delivery"
    }
    
    engine = KPIStorytellingEngine()
    result = engine.run_pipeline(
        scenario_id="SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
        user_role=UserClearance.EXECUTIVE_VP,
        primary_llm="mock",
        bluesky_llm="mock"
    )
    
    master_payload = result.get("master_payload")
    assert master_payload is not None
    # Depending on how it routes, it should eventually hit MAX_ITERATIONS_REACHED or REJECTED.
    # We assert it did NOT get an "APPROVED" or "PENDING" status, meaning the critic caught it.
    assert "MAX_ITERATIONS_REACHED" in master_payload.supervisor_status or "REJECTED" in master_payload.supervisor_status
