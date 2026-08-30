"""
Unified Master JSON Schema (Version 3.0) & Telemetry Contracts (§4.4, §12)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AnchorReferenceBlock(BaseModel):
    metric: str
    primary_driver: str
    causal_weight: float
    security_applied: str  # e.g. "TIER_2_TOKEN_MASKING", "PUBLIC_UNRESTRICTED"


class RecommendedActionBlock(BaseModel):
    action_id: str
    action: str
    estimated_cost_usd: float
    time_to_impact_minutes: int
    raci_owner: str
    approval_status: str  # "AUTO_APPROVED", "PENDING_VP_APPROVAL", "DISCARDED"
    source_layer: Optional[str] = None
    model_confidence_weight: Optional[float] = None
    critic_verdict: Optional[str] = None
    requires_shadow_run: bool = False


class ExecutiveViewBlock(BaseModel):
    financial_impact_usd: float
    business_risk_level: str  # "HIGH", "MEDIUM", "LOW"
    recommended_actions: List[RecommendedActionBlock]


class ExecutionPlaybookBlock(BaseModel):
    command: str
    target_environment: str


class EngineerViewBlock(BaseModel):
    technical_root_cause: str
    system_logs: List[str]
    execution_playbook: ExecutionPlaybookBlock


class OpsViewBlock(BaseModel):
    operational_bottleneck: str
    sla_impact: str
    mitigation_steps: List[str]


class DiscardedCandidateBlock(BaseModel):
    action: str
    source_layer: str
    critic_verdict: str


class RuntimeMetadataBlock(BaseModel):
    execution_latency_ms: int
    total_tokens_consumed: int
    estimated_cost_usd: float
    model_routed: str
    cache_hit: bool = False
    budget_pruning_applied: bool = False


class UnifiedMasterPayload(BaseModel):
    """Unified Master Executive JSON Schema (Version 3.0)."""
    anchor_reference: AnchorReferenceBlock
    executive_view: ExecutiveViewBlock
    engineer_view: EngineerViewBlock
    ops_view: Optional[OpsViewBlock] = None
    discarded_candidates: List[DiscardedCandidateBlock] = Field(default_factory=list)
    runtime_metadata: RuntimeMetadataBlock
    supervisor_status: str = "SCHEMA_VALID"
