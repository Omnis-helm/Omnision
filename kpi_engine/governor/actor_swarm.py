"""
Multi-Model Actor Swarm & Federated Persona Generation (§4.1, §9, §12.2)
"""

from typing import Dict, List, Any
from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.suggester.layers_data import SolutionCandidate
from kpi_engine.governor.schemas import (
    ExecutiveViewBlock,
    EngineerViewBlock,
    OpsViewBlock,
    ExecutionPlaybookBlock,
    RecommendedActionBlock,
)


class ActorSwarm:
    """Dispatches parallel generation tasks to specialized personas with model confidence weights."""

    def __init__(self):
        # Initial Model Confidence Weights (Wm)
        self.model_weights: Dict[str, float] = {
            "finance_agent": 0.92,
            "tech_agent": 0.94,
            "ops_agent": 0.88,
            "challenger_agent": 0.65,
        }

    def generate_executive_view(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
        passed_candidates: List[SolutionCandidate],
        context: Dict[str, Any],
    ) -> ExecutiveViewBlock:
        """Finance Agent: Generates financial impact, risk level, and executive recommendations."""
        fin_impact = context.get("financial_impact_usd", abs(anchor.variance_pct) * 3500.0)

        # Risk rating based on financial impact & z-score
        if fin_impact >= 30000.0 or anchor.z_score >= 5.0:
            risk_level = "HIGH"
        elif fin_impact >= 10000.0 or anchor.z_score >= 3.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        rec_actions = []
        for cand in passed_candidates:
            rec_actions.append(
                RecommendedActionBlock(
                    action_id=cand.action_id,
                    action=cand.action,
                    estimated_cost_usd=cand.estimated_cost_usd,
                    time_to_impact_minutes=cand.time_to_impact_minutes,
                    raci_owner=cand.raci_owner,
                    approval_status=cand.approval_status,
                    source_layer=cand.source_layer,
                    model_confidence_weight=cand.model_confidence_weight,
                    critic_verdict=cand.critic_verdict,
                )
            )

        return ExecutiveViewBlock(
            financial_impact_usd=round(fin_impact, 2),
            business_risk_level=risk_level,
            recommended_actions=rec_actions,
        )

    def generate_engineer_view(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
        passed_candidates: List[SolutionCandidate],
    ) -> EngineerViewBlock:
        """Technical Agent: Generates technical root cause, system logs, and execution command."""
        tech_root_cause = primary_driver.content
        sys_logs = [primary_driver.metadata.get("source_log", f"LOG_ERR_{primary_driver.node_id}")]

        # Pick primary technical command from top passed candidate
        primary_cand = passed_candidates[0] if passed_candidates else None
        cmd = primary_cand.technical_command if primary_cand and primary_cand.technical_command else "echo 'No automated script available'"
        env = primary_cand.target_environment if primary_cand and primary_cand.target_environment else "production"

        return EngineerViewBlock(
            technical_root_cause=tech_root_cause,
            system_logs=sys_logs,
            execution_playbook=ExecutionPlaybookBlock(
                command=cmd,
                target_environment=env,
            ),
        )

    def generate_ops_view(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
        passed_candidates: List[SolutionCandidate],
    ) -> OpsViewBlock:
        """Operations Agent: Generates operational bottleneck and SLA mitigation."""
        return OpsViewBlock(
            operational_bottleneck=f"{primary_driver.title} affecting {anchor.dimensions.get('region', 'Global')} region",
            sla_impact="Customer checkout completion SLA breach window: active",
            mitigation_steps=[c.action for c in passed_candidates],
        )
