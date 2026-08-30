"""
Pre-configured Enterprise Scenarios and Evidence Catalogs
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from kpi_engine.data.models import (
    CandidateNode,
    CandidateNodeType,
    SecurityTier,
    UserClearance,
    AnchorNode,
    LifecycleStage,
)


def get_scenario_1_stripe_outage(base_time: datetime) -> Dict[str, Any]:
    """Scenario 1: West Region Checkout Conversion Drop (-12.4%) due to Stripe v4.1 Gateway Latency."""
    anchor = AnchorNode(
        kpi_id="KPI_WEST_CHECKOUT_CONV",
        metric_name="West Region Checkout Conversion Rate",
        timestamp=base_time,
        current_value=2.80,
        baseline_mean=3.20,
        baseline_std=0.077,
        variance_pct=-12.50,
        z_score=5.19,  # Severe shock (Z > 5.0)
        lifecycle_stage=LifecycleStage.MATURE,
        dimensions={"region": "West", "platform": "iOS", "domain": "downstream"},
        trigger_rule="Z_SCORE_ANOMALY",
    )

    evidence_pool = [
        CandidateNode(
            node_id="NODE-SYS-101",
            node_type=CandidateNodeType.SYSTEM_LOG,
            title="Payment Gateway Latency Spike",
            content="Payment Gateway API Timeout (Stripe v4.1), 8000ms latency on POST /v1/charges",
            timestamp=base_time - timedelta(hours=2),
            dimensions={"region": "West", "platform": "iOS", "service": "payment-gateway"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"latency_ms": 8000.0, "error_rate": 0.34, "drop_contrib": 0.72},
            metadata={"source_log": "LOG_ERR_STRIPE_TIMEOUT_8000MS", "layer": "downstream"},
        ),
        CandidateNode(
            node_id="NODE-SUP-202",
            node_type=CandidateNodeType.SUPPORT_TICKET_CLUSTER,
            title="Zendesk Support Ticket Cluster",
            content="142 users reported spinning wheel on checkout and failed payment confirmation",
            timestamp=base_time - timedelta(hours=1, minutes=30),
            dimensions={"region": "West", "platform": "iOS", "queue": "checkout-friction"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"ticket_count": 142.0, "sentiment_score": -0.82, "drop_contrib": 0.24},
            metadata={"zendesk_tag": "TICKET_PAYMENT_FAILURE", "layer": "downstream"},
        ),
        CandidateNode(
            node_id="NODE-MKT-303",
            node_type=CandidateNodeType.MARKETING_LOG,
            title="West Region Marketing Email Campaign",
            content="Promotional blast email sent to West Region customer segment offering free shipping",
            timestamp=base_time - timedelta(hours=30),
            dimensions={"region": "West", "platform": "All", "channel": "email"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"volume_sent": 50000.0, "open_rate": 0.22, "drop_contrib": 0.00},
            metadata={"campaign_id": "CAMP_SUMMER_WEST", "layer": "downstream"},
        ),
        CandidateNode(
            node_id="NODE-OPS-404",
            node_type=CandidateNodeType.OPERATIONAL_LOG,
            title="East Region Warehouse Maintenance",
            content="Scheduled maintenance on East Region automated packaging conveyor belt",
            timestamp=base_time - timedelta(hours=12),
            dimensions={"region": "East", "platform": "Warehouse", "facility": "East-DC1"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"downtime_hours": 3.0, "drop_contrib": 0.00},
            metadata={"facility": "DC1", "layer": "midstream"},
        ),
    ]

    return {
        "scenario_id": "SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
        "title": "West Region Checkout Conversion Drop (-12.4%)",
        "anchor": anchor,
        "evidence_pool": evidence_pool,
        "context": {
            "cogs_moved": False,
            "ltv_moved": True,
            "financial_impact_usd": 42000.0,
            "expected_primary_driver": "Payment Gateway API Timeout (Stripe v4.1)",
        },
    }


def get_scenario_2_multivariate_price_volume(base_time: datetime) -> Dict[str, Any]:
    """Scenario 2: Net Revenue Drop (-13.7%) with Interacting Price and Volume Drivers + SHAP Ambient Variables."""
    anchor = AnchorNode(
        kpi_id="KPI_REVENUE_WEST",
        metric_name="West Region Daily Net Revenue",
        timestamp=base_time,
        current_value=302000.0,
        baseline_mean=350000.0,
        baseline_std=11800.0,
        variance_pct=-13.71,
        z_score=4.07,
        lifecycle_stage=LifecycleStage.MATURE,
        dimensions={"region": "West", "domain": "financials"},
        trigger_rule="Z_SCORE_ANOMALY",
    )

    # Multi-factor interacting drivers:
    # R = P * V
    # Base: P = $100, V = 3500 units => $350,000
    # Current: P = $92 (ΔP = -$8), V = 3282.6 units (ΔV = -217.4 units)
    # ΔR = P*ΔV + V*ΔP + ΔP*ΔV
    evidence_pool = [
        CandidateNode(
            node_id="NODE-PRC-201",
            node_type=CandidateNodeType.OPERATIONAL_LOG,
            title="Price Discounting Intervention",
            content="Aggressive price discount applied across Electronics catalog (Average Price -$8/unit)",
            timestamp=base_time - timedelta(hours=6),
            dimensions={"region": "West", "category": "Electronics"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"delta_p": -8.0, "p_base": 100.0, "v_base": 3500.0},
            metadata={"driver_type": "price_change"},
        ),
        CandidateNode(
            node_id="NODE-VOL-202",
            node_type=CandidateNodeType.OPERATIONAL_LOG,
            title="Order Volume Contraction",
            content="Order volume declined by 217.4 units due to concurrent competitor campaign",
            timestamp=base_time - timedelta(hours=5),
            dimensions={"region": "West", "category": "Electronics"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"delta_v": -217.4, "p_base": 100.0, "v_base": 3500.0},
            metadata={"driver_type": "volume_change"},
        ),
        CandidateNode(
            node_id="NODE-COMP-203",
            node_type=CandidateNodeType.COMPETITOR_ACTION,
            title="Competitor Mega Flash Sale",
            content="Competitor RivalRetail launched a 20% flash promotion on identical electronics SKUs",
            timestamp=base_time - timedelta(hours=8),
            dimensions={"region": "West", "competitor": "RivalRetail"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"promo_discount": 0.20, "market_share_shift": 0.04},
            metadata={"driver_type": "ambient_competitor"},
        ),
        CandidateNode(
            node_id="NODE-MACRO-204",
            node_type=CandidateNodeType.MACRO_INDICATOR,
            title="Severe Regional Heatwave & Grid Alert",
            content="Severe heatwave in West Coast metro areas causing peak electricity demand curtailment",
            timestamp=base_time - timedelta(hours=18),
            dimensions={"region": "West", "category": "Weather"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"temperature_delta_f": 18.0, "grid_alert_level": 2.0},
            metadata={"driver_type": "ambient_weather"},
        ),
    ]

    return {
        "scenario_id": "SCENARIO_2_MULTIVARIATE_DAG_SHAP",
        "title": "West Region Daily Net Revenue Drop (-13.7%) - Interacting Drivers",
        "anchor": anchor,
        "evidence_pool": evidence_pool,
        "context": {
            "cogs_moved": False,
            "ltv_moved": True,
            "financial_impact_usd": 48000.0,
            "p_base": 100.0,
            "v_base": 3500.0,
            "delta_p": -8.0,
            "delta_v": -217.4,
        },
    }


def get_scenario_3_cold_start_kpi(base_time: datetime) -> Dict[str, Any]:
    """Scenario 3: Cold-Start KPI Phased Handover (N < 30 samples)."""
    anchor = AnchorNode(
        kpi_id="KPI_COLD_NEW_CHECKOUT_FLOW",
        metric_name="New 1-Click Mobile Checkout Conversion",
        timestamp=base_time,
        current_value=3.70,
        baseline_mean=4.10,  # from EWMA/Surrogate
        baseline_std=0.15,
        variance_pct=-9.75,
        z_score=2.67,
        lifecycle_stage=LifecycleStage.COLD_START,
        dimensions={"platform": "Mobile", "domain": "downstream"},
        trigger_rule="COLD_START_TRIPWIRE",  # Tripped because 9.75% > 5% static tripwire
    )

    evidence_pool = [
        CandidateNode(
            node_id="NODE-COLD-301",
            node_type=CandidateNodeType.SYSTEM_LOG,
            title="Mobile SDK Biometric Timeout",
            content="FaceID / TouchID biometric auth failure on iOS 1-click checkout flow (v1.0.1)",
            timestamp=base_time - timedelta(hours=3),
            dimensions={"platform": "Mobile", "os": "iOS"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"auth_failure_rate": 0.18, "drop_contrib": 0.65},
            metadata={"sdk_version": "v1.0.1", "layer": "downstream"},
        ),
    ]

    return {
        "scenario_id": "SCENARIO_3_COLD_START_PHASED_HANDOVER",
        "title": "Cold-Start 1-Click Mobile Conversion Anomaly (-9.7%)",
        "anchor": anchor,
        "evidence_pool": evidence_pool,
        "context": {
            "kpi_id": "KPI_COLD_NEW_CHECKOUT_FLOW",
            "sample_count": 6,
            "surrogate_reference": "KPI_EAST_CHECKOUT_CONV",
            "static_tripwire": 0.05,
            "graduation_threshold": 30,
        },
    }


def get_scenario_4_security_clearance(base_time: datetime) -> Dict[str, Any]:
    """Scenario 4: Hybrid Security Matrix - Tier 1 Domain Pruning vs Tier 2 Token Masking."""
    anchor = AnchorNode(
        kpi_id="KPI_GROSS_MARGIN_WEST",
        metric_name="West Region Gross Margin",
        timestamp=base_time,
        current_value=38.20,
        baseline_mean=42.50,
        baseline_std=0.60,
        variance_pct=-10.12,
        z_score=7.17,  # Severe Shock
        lifecycle_stage=LifecycleStage.MATURE,
        dimensions={"region": "West", "domain": "financials"},
        trigger_rule="Z_SCORE_ANOMALY",
    )

    evidence_pool = [
        # Tier 1 Strategic Secret: Pruned completely if unauthorized
        CandidateNode(
            node_id="NODE-SEC-401",
            node_type=CandidateNodeType.EXECUTIVE_STRATEGIC,
            title="Unannounced M&A Integration Due Diligence",
            content="Confidential acquisition of FastPay checkout gateway incurrence of $850,000 non-recurring advisor fee",
            timestamp=base_time - timedelta(hours=4),
            dimensions={"region": "West", "entity": "M&A_Confidential"},
            security_tier=SecurityTier.TIER_1_DOMAIN_PRUNING,
            clearance_required=UserClearance.EXECUTIVE_VP,
            raw_metric_values={"advisor_fee_usd": 850000.0, "margin_impact_pct": -3.20},
            metadata={"secret_type": "M&A", "layer": "financials"},
        ),
        # Tier 2 Token-Level Masking: Retained in graph for math, masked for LLM
        CandidateNode(
            node_id="NODE-SEC-402",
            node_type=CandidateNodeType.OPERATIONAL_LOG,
            title="Vendor SLA Contract Penalty Fee",
            content="Expedited shipping SLA default penalty fee of $84,500 assessed against regional 3PL logistics provider",
            timestamp=base_time - timedelta(hours=6),
            dimensions={"region": "West", "vendor": "3PL_Carrier_X"},
            security_tier=SecurityTier.TIER_2_TOKEN_MASKING,
            clearance_required=UserClearance.JUNIOR_ANALYST,
            raw_metric_values={"penalty_amount_usd": 84500.0, "margin_impact_pct": -1.10},
            metadata={"vendor": "3PL_Carrier_X", "layer": "upstream"},
        ),
        # Public Unrestricted Node
        CandidateNode(
            node_id="NODE-SEC-403",
            node_type=CandidateNodeType.SUPPLIER_NOTICE,
            title="Semiconductor Component Tariff Surcharge",
            content="Supplier notice: 4.5% tariff surcharge applied across all Tier 1 microcontrollers",
            timestamp=base_time - timedelta(hours=14),
            dimensions={"region": "West", "category": "Semiconductors"},
            security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
            clearance_required=UserClearance.PUBLIC,
            raw_metric_values={"tariff_rate": 0.045, "margin_impact_pct": -0.65},
            metadata={"layer": "upstream"},
        ),
    ]

    return {
        "scenario_id": "SCENARIO_4_SECURITY_CLEARANCE_MATRIX",
        "title": "Gross Margin Drop (-10.1%) with Strategic Confidential Entities",
        "anchor": anchor,
        "evidence_pool": evidence_pool,
        "context": {
            "cogs_moved": True,
            "ltv_moved": False,
            "financial_impact_usd": 120000.0,
        },
    }
