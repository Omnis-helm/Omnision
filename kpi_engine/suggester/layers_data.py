"""
5-Layer Prescriptive Data Architecture for the Suggestion Network (§3.1, §7)

Layer 1  Internal SOPs / runbooks / post-mortems (grows via dynamic playbook appends)
Layer 2  External market precedents (public post-mortems, peer filings)
Layer 3  Active operational levers (contracts, feature flags, kill switches) + lever-backed actions
Layer 4  RACI authority limits
Layer 5  Blue-Sky challenger ideas (generated at runtime, never stored here)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class SolutionCandidate(BaseModel):
    action_id: str
    action: str
    source_layer: str
    model_confidence_weight: float = 0.85
    estimated_cost_usd: float = 0.0
    time_to_impact_minutes: int = 15
    raci_owner: str = "Platform Reliability (PagerDuty: on-call)"
    approval_status: str = "PENDING_REVIEW"
    critic_verdict: Optional[str] = None
    technical_command: Optional[str] = None
    target_environment: Optional[str] = None
    operational_lever_required: Optional[str] = None
    addresses_node_id: Optional[str] = None
    match_score: float = 0.0
    agent_key: str = "tech_agent"
    min_clearance: Optional[str] = None
    requires_shadow_run: bool = False


class PrescriptiveLayersStore:
    """In-memory repository representing the operational data layers."""

    def __init__(self):
        # ---------------- Layer 1: internal playbooks ----------------
        self.layer_1_playbooks: List[Dict[str, Any]] = [
            {
                "id": "PM-2291",
                "trigger_pattern": "payment gateway latency timeout stripe",
                "action": "Roll back Stripe v4.1 gateway integration to v4.0",
                "command": "helm rollback stripe-gateway 4.0",
                "target_environment": "prod-west",
                "cost_usd": 0.0,
                "time_minutes": 15,
                "raci": "Platform Reliability (PagerDuty: on-call)",
                "required_lever": "helm_rollback_capability",
            },
            {
                "id": "PB-PRICE-17",
                "trigger_pattern": "price discount promotion competitor electronics",
                "action": "Cap Electronics discount depth at 3% and price-match RivalRetail only on the top 5 overlapping SKUs",
                "command": "pricing-cli guardrail set --category electronics --max-discount 3 && pricing-cli price-match --competitor RivalRetail --top-skus 5",
                "target_environment": "pricing-engine-prod",
                "cost_usd": 6800.0,
                "time_minutes": 60,
                "raci": "Head of Pricing",
                "required_lever": "dynamic_pricing_engine",
            },
            {
                "id": "PB-MOB-311",
                "trigger_pattern": "biometric auth faceid touchid sdk mobile checkout",
                "action": "Disable the biometric step in 1-click checkout via feature flag (fall back to PIN) and ship SDK hotfix v1.0.2",
                "command": "ld-cli flag set checkout.biometric_step false --env prod && fastlane ios release --version 1.0.2",
                "target_environment": "mobile-prod",
                "cost_usd": 0.0,
                "time_minutes": 20,
                "raci": "Mobile Platform Team",
                "required_lever": "launchdarkly_feature_flags",
            },
            {
                "id": "FIN-ACC-07",
                "trigger_pattern": "m&a acquisition advisor fee non-recurring",
                "action": "Reclassify the M&A advisor fee as a non-recurring charge against the corporate reserve and report adjusted gross margin",
                "command": "erp-cli journal create --type NON_RECURRING --account CORP_RESERVE --ref MA-FASTPAY",
                "target_environment": "erp-finance",
                "cost_usd": 0.0,
                "time_minutes": 240,
                "raci": "Corporate Controller",
                "required_lever": "corporate_reserve_accrual",
                "min_clearance": "EXECUTIVE_VP",
            },
            {
                "id": "OPS-3PL-12",
                "trigger_pattern": "logistics sla fee vendor expedited",
                "action": "Invoke the SLA penalty recovery clause with 3PL_Carrier_X and re-route expedited West orders to the secondary carrier",
                "command": "tms-cli carrier reroute --region west --service expedited --to SecondaryCarrier",
                "target_environment": "transport-mgmt-prod",
                "cost_usd": 3500.0,
                "time_minutes": 180,
                "raci": "VP Logistics",
                "required_lever": "secondary_carrier_contract",
            },
            {
                "id": "SOP-808",
                "trigger_pattern": "tariff price shock components procurement microcontroller",
                "action": "Trigger primary vendor price hedge clause and dual-source microcontrollers from Taiwan fab",
                "command": "supply-chain-cli route-order --vendor TaiwanFabB --contract HEDGE-2026",
                "target_environment": "erp-procurement",
                "cost_usd": 45000.0,
                "time_minutes": 1440,
                "raci": "VP Supply Chain",
                "required_lever": "taiwan_fab_secondary_contract",
            },
        ]

        # ---------------- Layer 2: external market precedents ----------------
        self.layer_2_market_precedents: List[Dict[str, Any]] = [
            {
                "id": "EXT-GH-2024",
                "source": "GitHub Public Post-Mortem 2024",
                "trigger_pattern": "payment gateway timeout latency connection pool",
                "action": "Isolate the payment API connection pool and enable a circuit breaker at the Envoy proxy",
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
                "trigger_pattern": "competitor promotion volume drop electronics",
                "action": "Launch targeted loyalty member bundle bonus instead of blanket price matching",
                "command": "marketing-engine activate-promo --campaign LOYALTY_SHIELD",
                "target_environment": "crm-production",
                "cost_usd": 15000.0,
                "time_minutes": 60,
                "raci": "Head of Growth",
                "required_lever": "loyalty_bonus_engine",
            },
        ]

        # ---------------- Layer 3: active operational levers ----------------
        self.layer_3_active_levers: Dict[str, bool] = {
            "helm_rollback_capability": True,
            "stripe_backup_gateway_contract": True,  # active contract with Adyen
            "envoy_service_mesh": True,
            "loyalty_bonus_engine": True,
            "dynamic_pricing_engine": True,
            "launchdarkly_feature_flags": True,
            "corporate_reserve_accrual": True,
            "secondary_carrier_contract": True,
            "taiwan_fab_secondary_contract": True,
            "aws_direct_contract": False,  # no contract with an alternative cloud provider
        }
        self.layer_3_lever_actions: List[Dict[str, Any]] = [
            {
                "id": "LEV-301",
                "trigger_pattern": "payment gateway stripe latency timeout",
                "action": "Shift 15% of West Region payment traffic to the Adyen backup gateway",
                "command": "traffic-router set --region west --split stripe:85,adyen:15",
                "target_environment": "prod-traffic-mesh",
                "cost_usd": 6200.0,
                "time_minutes": 45,
                "raci": "VP Engineering",
                "required_lever": "stripe_backup_gateway_contract",
            },
        ]

        # ---------------- Layer 4: RACI directory ----------------
        self.layer_4_raci_limits = {
            "auto_approve_ceiling": 10000.0,
            "vp_approval_floor": 100000.0,
        }

    def append_dynamic_playbook(self, new_entry: Dict[str, Any]):
        """Dynamically ingests captured human modification back into Layer 1 (§3.1, §13)."""
        self.layer_1_playbooks.insert(0, new_entry)

    def lever_is_active(self, lever: Optional[str]) -> bool:
        return bool(lever) and self.layer_3_active_levers.get(lever, False)
