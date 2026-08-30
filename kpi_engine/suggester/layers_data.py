"""
5-Layer Prescriptive Data Architecture for the Suggestion Network (§3.1, §7)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SolutionCandidate(BaseModel):
    action_id: str
    action: str
    source_layer: str  # "Layer 1 - Internal Playbook", "Layer 2 - External Precedents", "Layer 3 - Operational Levers", "Layer 5 - Blue-Sky Challenger"
    model_confidence_weight: float = 0.85
    estimated_cost_usd: float = 0.0
    time_to_impact_minutes: int = 15
    raci_owner: str = "Platform Reliability (PagerDuty: on-call)"
    approval_status: str = "AUTO_APPROVED"  # "AUTO_APPROVED", "PENDING_VP_APPROVAL", "DISCARDED"
    critic_verdict: Optional[str] = None
    technical_command: Optional[str] = None
    target_environment: Optional[str] = None
    operational_lever_required: Optional[str] = None


class PrescriptiveLayersStore:
    """In-memory repository representing the 5 operational data layers."""

    def __init__(self):
        # Layer 1: Internal SOPs, runbooks, historical incident post-mortems
        self.layer_1_playbooks = [
            {
                "id": "PM-2291",
                "trigger_pattern": "payment gateway latency timeout stripe",
                "action": "Roll back Stripe v4.1 gateway integration",
                "command": "helm rollback stripe-gateway 4.0",
                "target_environment": "prod-west",
                "cost_usd": 0.0,
                "time_minutes": 15,
                "raci": "Platform Reliability (PagerDuty: on-call)",
                "required_lever": "helm_rollback_capability",
            },
            {
                "id": "SOP-808",
                "trigger_pattern": "tariff price shock components procurement",
                "action": "Trigger primary vendor price hedge clause and dual-source from Taiwan fab",
                "command": "supply-chain-cli route-order --vendor TaiwanFabB --contract HEDGE-2026",
                "target_environment": "erp-procurement",
                "cost_usd": 45000.0,
                "time_minutes": 120,
                "raci": "VP Supply Chain",
                "required_lever": "taiwan_fab_secondary_contract",
            },
        ]

        # Layer 2: External Market Precedents (Cloudflare, AWS, GitHub, SEC filings)
        self.layer_2_market_precedents = [
            {
                "id": "EXT-GH-2024",
                "source": "GitHub Public Post-Mortem 2024",
                "trigger_pattern": "payment gateway timeout connection pool exhaustion",
                "action": "Isolate API connection pool and enable circuit breaker at Envoy proxy",
                "command": "kubectl apply -f envoy-circuit-breaker.yaml",
                "target_environment": "prod-gateway-mesh",
                "cost_usd": 0.0,
                "time_minutes": 25,
                "raci": "DevOps Lead",
                "required_lever": "envoy_service_mesh",
            },
            {
                "id": "SEC-RTL-2025",
                "source": "Retail Peer SEC 10-Q Filing",
                "trigger_pattern": "competitor flash discount margin drop",
                "action": "Launch targeted loyalty member bundle bonus instead of direct price matching",
                "command": "marketing-engine activate-promo --campaign LOYALTY_SHIELD",
                "target_environment": "crm-production",
                "cost_usd": 15000.0,
                "time_minutes": 60,
                "raci": "Head of Growth",
                "required_lever": "loyalty_bonus_engine",
            },
        ]

        # Layer 3: Active Operational Levers (Feature flags, backup vendor contracts, kill switches)
        self.layer_3_active_levers = {
            "helm_rollback_capability": True,
            "stripe_backup_gateway_contract": True,  # Active contract with Adyen/Checkout.com
            "envoy_service_mesh": True,
            "loyalty_bonus_engine": True,
            "taiwan_fab_secondary_contract": True,
            "aws_direct_contract": False,  # No contract exists with alternative cloud provider!
        }

        # Layer 4: RACI Directory
        self.layer_4_raci_limits = {
            "auto_approve_ceiling": 10000.0,
            "vp_approval_floor": 100000.0,
        }

    def append_dynamic_playbook(self, new_entry: Dict[str, Any]):
        """Dynamically ingests captured human modification back into Layer 1 (§3.1, §13)."""
        self.layer_1_playbooks.insert(0, new_entry)
