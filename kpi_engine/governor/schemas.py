"""
Unified Master JSON Schema (Version 3.1) & Telemetry Contracts (§4.4, §12)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AnchorReferenceBlock(BaseModel):
    metric: str
    primary_driver: str
    primary_driver_id: Optional[str] = None
    causal_weight: float
    confidence: str = "HIGH"          # HIGH (W >= threshold) | LOW (best effort) | NONE
    security_applied: str             # PUBLIC_UNRESTRICTED | TIER_2_TOKEN_MASKING | ...


class RecommendedActionBlock(BaseModel):
    action_id: str
    action: str
    estimated_cost_usd: float
    time_to_impact_minutes: int
    expected_damage_reverted: Optional[str] = None
    raci_owner: str
    approval_status: str  # AUTO_APPROVED | PENDING_DIRECTOR_APPROVAL | PENDING_VP_APPROVAL | SANDBOX | PROMOTED_FROM_SANDBOX ...
    source_layer: Optional[str] = None
    model_confidence_weight: Optional[float] = None
    critic_verdict: Optional[str] = None
    supervisor_verdict: Optional[str] = None
    technical_command: Optional[str] = None
    target_environment: Optional[str] = None
    addresses_node_id: Optional[str] = None
    requires_shadow_run: bool = False


class ExecutiveViewBlock(BaseModel):
    financial_impact_usd: float
    business_risk_level: str  # HIGH | MEDIUM | LOW
    recommended_actions: List[RecommendedActionBlock]
    narrative: str = ""
    narrative_source: str = ""


class ExecutionPlaybookBlock(BaseModel):
    command: str
    target_environment: str


class EngineerViewBlock(BaseModel):
    technical_root_cause: str
    system_logs: List[str]
    execution_playbook: ExecutionPlaybookBlock
    additional_playbooks: List[ExecutionPlaybookBlock] = Field(default_factory=list)


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
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float
    model_routed: str
    orchestration_mode: str = "sequential"
    swarm_iterations: int = 0
    cache_hit: bool = False
    llm_cache_hits: int = 0
    budget_pruning_applied: bool = False
    llm_errors: List[str] = Field(default_factory=list)


class UnifiedMasterPayload(BaseModel):
    """Unified Master Executive JSON Schema."""
    anchor_reference: AnchorReferenceBlock
    executive_view: ExecutiveViewBlock
    engineer_view: EngineerViewBlock
    ops_view: Optional[OpsViewBlock] = None
    blue_sky_actions: List[RecommendedActionBlock] = Field(default_factory=list)
    discarded_candidates: List[DiscardedCandidateBlock] = Field(default_factory=list)
    runtime_metadata: RuntimeMetadataBlock
    supervisor_status: str = "SCHEMA_VALID"
