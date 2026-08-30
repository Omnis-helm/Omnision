"""
FastAPI REST API for the KPI Storytelling Engine (§4.4, §12.2)
"""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance
from kpi_engine.governor.schemas import UnifiedMasterPayload

app = FastAPI(
    title="Omnision: Autonomous KPI Storytelling Engine REST API",
    version="3.0.0",
    description="Omnision — Unified Architecture for Autonomous Anomaly Diagnosis, Solution Synthesis, Multi-Agent Governance & Continuous Learning",
)

# Global engine instance
engine = KPIStorytellingEngine()


class InvestigationRequest(BaseModel):
    scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"
    user_role: UserClearance = UserClearance.EXECUTIVE_VP
    force_refresh: bool = False


class RCAOverrideRequest(BaseModel):
    scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"
    demoted_node_id: str = "NODE-SYS-101"
    promoted_node_id: Optional[str] = None
    custom_injected_text: Optional[str] = None
    user_role: UserClearance = UserClearance.EXECUTIVE_VP


class ActionFeedbackRequest(BaseModel):
    action_id: str
    source_layer: str
    signal: str  # "ACCEPT", "REJECT", "MODIFY"
    user_id: str = "user_1"


class ExecuteActionRequest(BaseModel):
    base_action_id: str
    original_action: str
    modified_action: str
    modified_command: str
    engineer_id: str = "oncall_eng_1"
    target_environment: str = "prod-west"


@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "specification": "KPI Storytelling Engine Unified Architecture Compendium v3.0",
    }


@app.get("/api/scenarios")
def list_scenarios():
    return [
        {
            "id": "SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
            "name": "Stripe v4.1 Payment Gateway Outage (Downstream, -12.4%)",
            "kpi": "KPI_WEST_CHECKOUT_CONV",
            "key_aspects": ["Downstream Scoping", "Z-Score Shock", "Layer 1 Rollback", "Critic Rejection of Blue-Sky"],
        },
        {
            "id": "SCENARIO_2_MULTIVARIATE_DAG_SHAP",
            "name": "Price & Volume Interacting Drivers (Multivariate DAG + SHAP)",
            "kpi": "KPI_REVENUE_WEST",
            "key_aspects": ["Tier 1 Gold ΔR = PΔV + VΔP + ΔPΔV", "Tier 3 Bronze SHAP Game Theory", "Multicollinearity Decoupling"],
        },
        {
            "id": "SCENARIO_3_COLD_START_PHASED_HANDOVER",
            "name": "Cold-Start 1-Click Mobile Checkout (<30d, Phased Handover)",
            "kpi": "KPI_COLD_NEW_CHECKOUT_FLOW",
            "key_aspects": ["Phase 1 Static 5% Tripwire", "Phase 2 EWMA + Sibling Surrogate", "Phase 3 Graduation at N>=30"],
        },
        {
            "id": "SCENARIO_4_SECURITY_CLEARANCE_MATRIX",
            "name": "Hybrid Security Matrix (Strategic M&A Secret vs Token Masking)",
            "kpi": "KPI_GROSS_MARGIN_WEST",
            "key_aspects": ["Tier 1 Domain Pruning & Graceful Abstention", "Tier 2 Token Masking <REDACTED_DOLLAR_VALUE>"],
        },
    ]


@app.post("/api/investigate")
def run_investigation(req: InvestigationRequest):
    result = engine.run_pipeline(
        scenario_id=req.scenario_id,
        user_role=req.user_role,
        force_refresh=req.force_refresh,
    )
    if result["status"] == "ABSTAINED":
        return result

    # Return serialized payload with DAG info
    return {
        "status": "SUCCESS",
        "scenario_id": req.scenario_id,
        "user_role": req.user_role.value,
        "anchor": result["anchor"].model_dump(),
        "dag_graph": result["dag_payload"].model_dump(),
        "master_payload": result["master_payload"].model_dump(),
        "security_audit": result["security_audit"],
    }


@app.post("/api/override-rca")
def override_rca(req: RCAOverrideRequest):
    result = engine.handle_human_rca_override(
        scenario_id=req.scenario_id,
        demoted_node_id=req.demoted_node_id,
        promoted_node_id=req.promoted_node_id,
        custom_injected_text=req.custom_injected_text,
        user_role=req.user_role,
    )
    return result


@app.post("/api/feedback")
def submit_feedback(req: ActionFeedbackRequest):
    record = engine.trust_tuner.record_feedback(
        action_id=req.action_id,
        source_layer=req.source_layer,
        signal=req.signal,
        user_id=req.user_id,
    )
    return {"status": "FEEDBACK_LOGGED", "record": record, "current_weights": engine.supervisor.swarm.model_weights}


@app.post("/api/execute-action")
def execute_and_append_playbook(req: ExecuteActionRequest):
    new_pb = engine.playbook_appender.capture_execution_delta(
        base_action_id=req.base_action_id,
        original_action=req.original_action,
        modified_action=req.modified_action,
        modified_command=req.modified_command,
        engineer_id=req.engineer_id,
        target_environment=req.target_environment,
    )
    return {"status": "PLAYBOOK_INGESTED", "playbook_entry": new_pb, "total_layer1_playbooks": len(engine.layers_store.layer_1_playbooks)}


@app.get("/api/telemetry")
def get_telemetry():
    return {
        "cumulative_tokens_consumed": engine.supervisor.cumulative_token_spend,
        "cached_queries_count": len(engine.supervisor.semantic_cache),
        "model_weights": engine.supervisor.swarm.model_weights,
        "dynamic_playbooks_count": len(engine.playbook_appender.appended_records),
    }
