"""
Test Suite for Hybrid Security Matrix (§2.3, §4.3)
"""

import pytest
from datetime import datetime, timedelta

from kpi_engine.data.models import (
    CandidateNode,
    CandidateNodeType,
    SecurityTier,
    UserClearance,
)
from kpi_engine.scoper.security_matrix import HybridSecurityMatrix


def test_tier_1_domain_pruning_unauthorized():
    """Verify that strategic secret nodes are completely pruned and trigger graceful abstention."""
    sec = HybridSecurityMatrix()
    base_time = datetime(2026, 8, 30, 10, 0, 0)

    secret_node = CandidateNode(
        node_id="NODE-MA-001",
        node_type=CandidateNodeType.EXECUTIVE_STRATEGIC,
        title="Unannounced M&A Acquisition",
        content="Confidential acquisition of QuickPay incurring $850,000 advisor fee",
        timestamp=base_time - timedelta(hours=2),
        security_tier=SecurityTier.TIER_1_DOMAIN_PRUNING,
        clearance_required=UserClearance.EXECUTIVE_VP,
        raw_metric_values={"margin_impact_pct": -3.50},
    )

    public_node = CandidateNode(
        node_id="NODE-PUB-002",
        node_type=CandidateNodeType.SUPPLIER_NOTICE,
        title="General Supplier Tariff Notice",
        content="Supplier announced minor 1% packaging adjustment",
        timestamp=base_time - timedelta(hours=5),
        security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
        clearance_required=UserClearance.PUBLIC,
    )

    nodes = [secret_node, public_node]

    # Junior Analyst runs engine
    cleared_nodes, audit = sec.apply_security_governance(nodes, UserClearance.JUNIOR_ANALYST)

    assert len(cleared_nodes) == 1
    assert cleared_nodes[0].node_id == "NODE-PUB-002"
    assert audit["pruned_nodes_count"] == 1
    assert audit["abstain_recommended"] is True
    assert "Insufficient authorized evidence" in audit["abstain_reason"]


def test_tier_2_token_masking_junior_analyst():
    """Verify that operational confidentiality nodes retain causal math but mask dollar figures."""
    sec = HybridSecurityMatrix()
    base_time = datetime(2026, 8, 30, 10, 0, 0)

    penalty_node = CandidateNode(
        node_id="NODE-PEN-003",
        node_type=CandidateNodeType.OPERATIONAL_LOG,
        title="Vendor SLA Penalty of $84,500 assessed",
        content="Carrier breached turnaround SLA and was fined $84,500.00 in contract damages",
        timestamp=base_time - timedelta(hours=3),
        security_tier=SecurityTier.TIER_2_TOKEN_MASKING,
        clearance_required=UserClearance.SENIOR_ENGINEER,
        raw_metric_values={"penalty_amount_usd": 84500.0},
    )

    cleared_nodes, audit = sec.apply_security_governance([penalty_node], UserClearance.JUNIOR_ANALYST)

    assert len(cleared_nodes) == 1
    masked_node = cleared_nodes[0]
    assert masked_node.is_masked is True
    assert "$84,500" not in masked_node.content
    assert "<REDACTED_DOLLAR_VALUE>" in masked_node.content
    assert "<REDACTED_DOLLAR_VALUE>" in masked_node.title
    assert audit["masked_nodes_count"] == 1
    assert audit["abstain_recommended"] is False
