"""
FastAPI REST API for the Omnision KPI Storytelling Engine.

    uvicorn kpi_engine.api.app:app --reload

Authentication: POST /api/login with username/password -> bearer token. Every other endpoint (except
/api/health and /api/scenarios) requires `Authorization: Bearer <token>`. The caller's role always
comes from the token, never from the request body.
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel

from kpi_engine import __version__
from kpi_engine.auth import authenticate, issue_token, verify_token, require_clearance
from kpi_engine.data.models import UserClearance
from kpi_engine.pipeline import KPIStorytellingEngine, SCENARIOS

app = FastAPI(
    title="Omnision: Autonomous KPI Storytelling Engine REST API",
    version=__version__,
    description="Anomaly diagnosis, causal inference, governed solution synthesis and continuous learning.",
)
engine = KPIStorytellingEngine()


# ----------------------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    username: str
    password: str


class Principal(BaseModel):
    username: str
    role: UserClearance


def current_user(authorization: Optional[str] = Header(default=None)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    verified = verify_token(authorization.split(" ", 1)[1].strip())
    if verified is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return Principal(username=verified[0], role=verified[1])


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------------------------------- models
class InvestigationRequest(BaseModel):
    scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"
    force_refresh: bool = False
    primary_llm: str = "mock"
    bluesky_llm: str = "mock"


class RCAOverrideRequest(BaseModel):
    scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"
    demoted_node_id: Optional[str] = None
    promoted_node_id: Optional[str] = None
    custom_injected_text: Optional[str] = None
    is_noise: bool = False
    primary_llm: str = "mock"
    bluesky_llm: str = "mock"


class RejectFixRequest(BaseModel):
    scenario_id: str
    action_text: str
    action_id: Optional[str] = None
    source_layer: Optional[str] = None
    primary_llm: str = "mock"
    bluesky_llm: str = "mock"


class ActionFeedbackRequest(BaseModel):
    scenario_id: str
    action_id: str
    source_layer: str
    action_text: str
    modified_action: Optional[str] = None
    modified_command: Optional[str] = None
    root_cause_text: Optional[str] = None
    target_environment: str = "production"


def _serialize(result: dict) -> dict:
    out = {"status": result["status"], "scenario_id": result.get("scenario_id")}
    if result.get("anchor") is not None:
        out["anchor"] = result["anchor"].model_dump(mode="json")
    for key in ("reason", "security_audit", "detection", "noise_verdict", "cache_hit"):
        if key in result:
            out[key] = result[key]
    if result.get("dag_payload") is not None:
        out["dag_graph"] = result["dag_payload"].model_dump(mode="json")
    if result.get("master_payload") is not None:
        out["master_payload"] = result["master_payload"].model_dump(mode="json")
    return out


# ----------------------------------------------------------------------------- endpoints
@app.get("/api/health")
def get_health():
    return {"status": "healthy", "version": __version__}


@app.post("/api/login")
def login(req: LoginRequest):
    role = authenticate(req.username, req.password)
    if role is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": issue_token(req.username, role), "token_type": "bearer", "role": role.value}


@app.get("/api/scenarios")
def list_scenarios():
    return [{"id": sid, "title": fn(engine.base_time)["title"], "kpi": fn(engine.base_time)["anchor"].kpi_id}
            for sid, fn in SCENARIOS.items()]


@app.get("/api/fleet-scan")
def fleet_scan(user: Principal = Depends(current_user)):
    return [a.model_dump(mode="json") for a in engine.scan_fleet()]


@app.post("/api/investigate")
def run_investigation(req: InvestigationRequest, user: Principal = Depends(current_user)):
    result = _guard(engine.run_pipeline, scenario_id=req.scenario_id, user_role=user.role,
                    force_refresh=req.force_refresh, primary_llm=req.primary_llm, bluesky_llm=req.bluesky_llm)
    return _serialize(result)


@app.post("/api/override-rca")
def override_rca(req: RCAOverrideRequest, user: Principal = Depends(current_user)):
    _guard(require_clearance, user.role, UserClearance.SENIOR_ENGINEER)
    res = _guard(engine.handle_human_rca_override, scenario_id=req.scenario_id, demoted_node_id=req.demoted_node_id,
                 promoted_node_id=req.promoted_node_id, custom_injected_text=req.custom_injected_text,
                 user_role=user.role, primary_llm=req.primary_llm, bluesky_llm=req.bluesky_llm,
                 is_noise=req.is_noise, analyst_id=user.username)
    return {"status": res["status"], "recalibration_record": res["recalibration_record"],
            "result": _serialize(res["result"])}


@app.post("/api/reject-fix")
def reject_fix(req: RejectFixRequest, user: Principal = Depends(current_user)):
    _guard(require_clearance, user.role, UserClearance.SENIOR_ENGINEER)
    res = _guard(engine.handle_rejected_fix, req.scenario_id, None, req.action_text, user.role, req.primary_llm,
                 req.bluesky_llm, action_id=req.action_id, source_layer=req.source_layer, user_id=user.username)
    return {"status": res["status"], "trust_feedback": res["trust_feedback"], "result": _serialize(res["result"])}


@app.post("/api/approve-fix")
def approve_fix(req: ActionFeedbackRequest, user: Principal = Depends(current_user)):
    _guard(require_clearance, user.role, UserClearance.SENIOR_ENGINEER)
    return _guard(engine.handle_accepted_fix, req.scenario_id, req.action_id, req.source_layer, req.action_text,
                  user_id=user.username, modified_action=req.modified_action, modified_command=req.modified_command,
                  root_cause_text=req.root_cause_text, target_environment=req.target_environment)


@app.post("/api/reset-learning")
def reset_learning(scenario_id: Optional[str] = None, user: Principal = Depends(current_user)):
    _guard(require_clearance, user.role, UserClearance.EXECUTIVE_VP)
    return engine.reset_learning(scenario_id)


@app.get("/api/telemetry")
def get_telemetry(user: Principal = Depends(current_user)):
    return {
        "cumulative_tokens_consumed": engine.supervisor.cumulative_token_spend,
        "cumulative_cost_usd": round(engine.supervisor.cumulative_cost_usd, 6),
        "cached_payloads": len(engine.supervisor.semantic_cache),
        "model_weights": engine.supervisor.swarm.model_weights,
        "layer1_playbooks": len(engine.layers_store.layer_1_playbooks),
        "dynamic_playbooks": len(engine.playbook_appender.appended_records),
        "semantic_threshold": engine.cr_scorer.semantic_threshold,
        "learning_version": engine.learning_version,
    }
