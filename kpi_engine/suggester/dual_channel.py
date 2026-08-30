"""
Dual-Channel Solution Suggestion Network: Grounded vs Blue-Sky Paths (§3.2, §8)
"""

from typing import List, Dict, Any
from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.suggester.layers_data import SolutionCandidate, PrescriptiveLayersStore


class DualChannelSuggester:
    """Generates candidate solutions via parallel Grounded (Channel A) and Challenger (Channel B) paths."""

    def __init__(self, layers_store: PrescriptiveLayersStore):
        self.store = layers_store

    def run_channel_a_grounded(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
    ) -> List[SolutionCandidate]:
        """Channel A: Grounded Path using internal SOPs, runbooks, and operational levers."""
        candidates = []
        driver_text = f"{primary_driver.title} {primary_driver.content}".lower()

        # 1. Match Layer 1 Playbooks (High confidence: 0.94)
        for pb in self.store.layer_1_playbooks:
            keywords = pb["trigger_pattern"].split()
            if any(k in driver_text for k in keywords):
                candidates.append(
                    SolutionCandidate(
                        action_id=f"ACT-{pb['id']}",
                        action=pb["action"],
                        source_layer=f"Layer 1 - Internal Playbook (past incident {pb['id']})",
                        model_confidence_weight=0.94,
                        estimated_cost_usd=pb["cost_usd"],
                        time_to_impact_minutes=pb["time_minutes"],
                        raci_owner=pb["raci"],
                        approval_status="AUTO_APPROVED" if pb["cost_usd"] < 10000 else "PENDING_VP_APPROVAL",
                        technical_command=pb.get("command"),
                        target_environment=pb.get("target_environment"),
                        operational_lever_required=pb.get("required_lever"),
                    )
                )

        # 2. Match Layer 3 Operational Levers (Confidence: 0.81)
        if "payment" in driver_text or "stripe" in driver_text or "gateway" in driver_text:
            candidates.append(
                SolutionCandidate(
                    action_id="ACT-LEV-301",
                    action="Shift 15% of West Region traffic to backup gateway",
                    source_layer="Layer 3 - Operational Levers (active backup contract)",
                    model_confidence_weight=0.81,
                    estimated_cost_usd=6200.0,
                    time_to_impact_minutes=45,
                    raci_owner="VP Engineering",
                    approval_status="AUTO_APPROVED",
                    technical_command="traffic-router set --region west --split stripe:85,adyen:15",
                    target_environment="prod-traffic-mesh",
                    operational_lever_required="stripe_backup_gateway_contract",
                )
            )

        # 3. Match Layer 2 Market Precedents (Confidence: 0.76)
        for prec in self.store.layer_2_market_precedents:
            keywords = prec["trigger_pattern"].split()
            if any(k in driver_text for k in keywords):
                candidates.append(
                    SolutionCandidate(
                        action_id=f"ACT-{prec['id']}",
                        action=prec["action"],
                        source_layer=f"Layer 2 - External Market Precedents ({prec['source']})",
                        model_confidence_weight=0.76,
                        estimated_cost_usd=prec["cost_usd"],
                        time_to_impact_minutes=prec["time_minutes"],
                        raci_owner=prec["raci"],
                        approval_status="AUTO_APPROVED" if prec["cost_usd"] < 10000 else "PENDING_VP_APPROVAL",
                        technical_command=prec.get("command"),
                        target_environment=prec.get("target_environment"),
                        operational_lever_required=prec.get("required_lever"),
                    )
                )

        return candidates

    def run_channel_b_challenger(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
    ) -> List[SolutionCandidate]:
        """Channel B: Blue-Sky LLM Challenger (Unconstrained Ideation)."""
        return [
            SolutionCandidate(
                action_id="ACT-CHAL-501",
                action="Migrate checkout to alternate cloud provider",
                source_layer="Layer 5 - Blue-Sky Challenger",
                model_confidence_weight=0.62,
                estimated_cost_usd=125000.0,
                time_to_impact_minutes=1440,
                raci_owner="CTO / VP Engineering",
                approval_status="PENDING_VP_APPROVAL",
                technical_command="terraform apply -target=aws_cluster_west",
                target_environment="cloud-infra",
                operational_lever_required="aws_direct_contract",
            )
        ]

    def generate_all_candidates(
        self,
        anchor: AnchorNode,
        primary_driver: CandidateNode,
    ) -> List[SolutionCandidate]:
        """Runs parallel generation and sorts candidates descending by model confidence weight."""
        grounded = self.run_channel_a_grounded(anchor, primary_driver)
        challenger = self.run_channel_b_challenger(anchor, primary_driver)
        all_cands = grounded + challenger
        # Sort descending by model confidence weight
        return sorted(all_cands, key=lambda c: c.model_confidence_weight, reverse=True)
