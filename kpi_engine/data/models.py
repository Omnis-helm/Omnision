"""
Data Models & Schema Contracts for the KPI Storytelling Engine
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class LifecycleStage(str, Enum):
    COLD_START = "COLD_START"
    MATURE = "MATURE"


class SecurityTier(str, Enum):
    PUBLIC_UNRESTRICTED = "PUBLIC_UNRESTRICTED"
    TIER_1_DOMAIN_PRUNING = "TIER_1_DOMAIN_PRUNING"   # Strategic secrets (M&A, HR terminations) -> Pruned if unauthorized
    TIER_2_TOKEN_MASKING = "TIER_2_TOKEN_MASKING"     # Operational confidentiality -> Masked as <REDACTED_DOLLAR_VALUE>


class UserClearance(str, Enum):
    PUBLIC = "PUBLIC"
    JUNIOR_ANALYST = "JUNIOR_ANALYST"
    SENIOR_ENGINEER = "SENIOR_ENGINEER"
    EXECUTIVE_VP = "EXECUTIVE_VP"
    ADMIN = "ADMIN"


class KPISemanticContract(BaseModel):
    kpi_id: str
    name: str
    domain: str  # 'financials', 'upstream', 'midstream', 'downstream', 'macro'
    lifecycle_stage: LifecycleStage = LifecycleStage.MATURE
    static_tripwire: float = 0.05
    surrogate_reference: Optional[str] = None
    graduation_threshold: int = 30
    unit: str = "USD"
    target_value: float = 100.0


class TelemetryPoint(BaseModel):
    timestamp: datetime
    kpi_id: str
    value: float
    dimensions: Dict[str, str] = Field(default_factory=dict)


class CandidateNodeType(str, Enum):
    SYSTEM_LOG = "System_Log"
    SUPPORT_TICKET_CLUSTER = "Support_Ticket_Cluster"
    MARKETING_LOG = "Marketing_Log"
    SUPPLIER_NOTICE = "Supplier_Notice"
    COMPETITOR_ACTION = "Competitor_Action"
    MACRO_INDICATOR = "Macro_Indicator"
    OPERATIONAL_LOG = "Operational_Log"
    EXECUTIVE_STRATEGIC = "Executive_Strategic"
    HISTORICAL_PRECEDENT = "Historical_Precedent"
    HISTORICAL_NOISE = "Historical_Noise"


class CandidateNode(BaseModel):
    node_id: str
    node_type: CandidateNodeType
    title: str
    content: str
    timestamp: datetime
    dimensions: Dict[str, str] = Field(default_factory=dict)
    security_tier: SecurityTier = SecurityTier.PUBLIC_UNRESTRICTED
    clearance_required: UserClearance = UserClearance.PUBLIC
    raw_metric_values: Dict[str, float] = Field(default_factory=dict)
    is_masked: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnchorNode(BaseModel):
    kpi_id: str
    metric_name: str
    timestamp: datetime
    current_value: float
    baseline_mean: float
    baseline_std: float
    variance_pct: float
    z_score: float
    lifecycle_stage: LifecycleStage
    dimensions: Dict[str, str] = Field(default_factory=dict)
    trigger_rule: str  # "Z_SCORE_ANOMALY" or "COLD_START_TRIPWIRE"
