"""
Multi-Model Actor Swarm & Federated Persona Generation (§4.1, §9, §12.2)

Holds the per-agent trust weights (Wm) tuned by human feedback, and renders the governed proposals
into the three persona views of the Unified Master Payload.
"""

from typing import Dict, List, Any, Optional

from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.governor.schemas import (
    ExecutiveViewBlock,
    EngineerViewBlock,
    OpsViewBlock,
    ExecutionPlaybookBlock,
    RecommendedActionBlock,
)
from kpi_engine.config import CONFIG

INITIAL_MODEL_WEIGHTS = {
    "finance_agent": 0.92,     # Layer 2 market precedents / finance persona
    "tech_agent": 0.94,        # Layer 1 internal playbooks
    "ops_agent": 0.88,         # Layer 3 operational levers
    "llm_swarm_agent": 0.85,   # free-form LLM proposals
    "challenger_agent": 0.65,  # Layer 5 blue-sky
}


def _get(p, key, default=None):
    return p.get(key, default) if isinstance(p, dict) else getattr(p, key, default)


class ActorSwarm:
    """Dispatches persona generation with model confidence weights."""

    def __init__(self):
        self.model_weights: Dict[str, float] = dict(INITIAL_MODEL_WEIGHTS)

    def risk_level(self, anchor: AnchorNode, financial_impact: float) -> str:
        if financial_impact >= 30000.0 or anchor.z_score >= CONFIG.z_score_shock_threshold:
            return "HIGH"
        if financial_impact >= 10000.0 or anchor.z_score >= CONFIG.z_score_alert_threshold:
            return "MEDIUM"
        return "LOW"

    def to_action_block(self, p, anchor: AnchorNode, requires_shadow_run: bool = False) -> RecommendedActionBlock:
        share = _get(p, "explained_share")
        reverted = (f"Up to {share * abs(anchor.variance_pct):.1f}% of the {abs(anchor.variance_pct):.1f}% KPI move"
                    if share else "Unquantified")
        return RecommendedActionBlock(
            action_id=_get(p, "action_id", "ACT-000"),
            action=_get(p, "action", ""),
            estimated_cost_usd=float(_get(p, "estimated_cost_usd", 0.0) or 0.0),
            time_to_impact_minutes=int(_get(p, "time_to_impact_minutes", 0) or 0),
            expected_damage_reverted=reverted,
            raci_owner=_get(p, "raci_owner", "Unassigned"),
            approval_status=_get(p, "approval_status", "PENDING_REVIEW"),
            source_layer=_get(p, "source_layer"),
            model_confidence_weight=_get(p, "model_confidence_weight"),
            critic_verdict=_get(p, "critic_verdict"),
            supervisor_verdict=_get(p, "supervisor_verdict"),
            technical_command=_get(p, "technical_command"),
            target_environment=_get(p, "target_environment"),
            addresses_node_id=_get(p, "addresses_node_id"),
            requires_shadow_run=requires_shadow_run or bool(_get(p, "requires_shadow_run", False)),
        )

    def generate_executive_view(self, anchor: AnchorNode, primary_driver: Optional[CandidateNode],
                                approved: List[Any], context: Dict[str, Any], narrative: str = "",
                                narrative_source: str = "") -> ExecutiveViewBlock:
        fin_impact = float(context.get("financial_impact_usd", abs(anchor.variance_pct) * 3500.0))
        return ExecutiveViewBlock(
            financial_impact_usd=round(fin_impact, 2),
            business_risk_level=self.risk_level(anchor, fin_impact),
            recommended_actions=[self.to_action_block(p, anchor) for p in approved],
            narrative=narrative,
            narrative_source=narrative_source,
        )

    def generate_engineer_view(self, anchor: AnchorNode, primary_driver: Optional[CandidateNode],
                               approved: List[Any], evidence: List[CandidateNode]) -> EngineerViewBlock:
        if primary_driver is not None:
            tech_root_cause = primary_driver.title if primary_driver.is_masked else primary_driver.content
        else:
            tech_root_cause = "No causal driver cleared the threshold - manual investigation required."
        logs = []
        for n in evidence[:5]:
            src = n.metadata.get("source_log") or n.metadata.get("zendesk_tag") or n.node_id
            logs.append(f"[{n.node_type.value}] {src}: {n.title if n.is_masked else n.content}")
        with_cmd = [p for p in approved if _get(p, "technical_command")]
        top = with_cmd[0] if with_cmd else None
        return EngineerViewBlock(
            technical_root_cause=tech_root_cause,
            system_logs=logs or [f"[WARN] Anomaly in {anchor.metric_name}"],
            execution_playbook=ExecutionPlaybookBlock(
                command=_get(top, "technical_command") if top else "echo 'No automated command - follow manual runbook'",
                target_environment=(_get(top, "target_environment") or "production") if top else "n/a",
            ),
            additional_playbooks=[
                ExecutionPlaybookBlock(command=_get(p, "technical_command"), target_environment=_get(p, "target_environment") or "production")
                for p in with_cmd[1:]
            ],
        )

    def generate_ops_view(self, anchor: AnchorNode, primary_driver: Optional[CandidateNode],
                          approved: List[Any]) -> OpsViewBlock:
        region = anchor.dimensions.get("region") or anchor.dimensions.get("platform") or "Global"
        title = primary_driver.title if primary_driver is not None else "Unexplained KPI movement"
        fastest = min((int(_get(p, "time_to_impact_minutes", 0) or 0) for p in approved), default=0)
        return OpsViewBlock(
            operational_bottleneck=f"{title} affecting {region}",
            sla_impact=(f"{anchor.metric_name} is {abs(anchor.variance_pct):.1f}% off baseline; "
                        f"fastest approved mitigation acts in ~{fastest} min"),
            mitigation_steps=[f"{_get(p, 'action')} — owner: {_get(p, 'raci_owner')} [{_get(p, 'approval_status')}]"
                              for p in approved],
        )
