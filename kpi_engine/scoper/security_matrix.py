"""
Hybrid Security Matrix: Tier 1 Domain Pruning & Tier 2 Token Masking (§2.3, §4.3)
"""

import re
from typing import List, Tuple, Dict, Any
from kpi_engine.data.models import (
    CandidateNode,
    SecurityTier,
    UserClearance,
    AnchorNode,
)


class HybridSecurityMatrix:
    """Applies role-based access control without corrupting causal diagnostic math."""

    CLEARANCE_LEVELS = {
        UserClearance.PUBLIC: 0,
        UserClearance.JUNIOR_ANALYST: 1,
        UserClearance.SENIOR_ENGINEER: 2,
        UserClearance.EXECUTIVE_VP: 3,
        UserClearance.ADMIN: 4,
    }

    # Lightweight PII Redaction
    PII_PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
    }

    def _redact_pii(self, text: str) -> str:
        """Dynamically scans and masks PII from raw text."""
        redacted_text = text
        for label, pattern in self.PII_PATTERNS.items():
            redacted_text = re.sub(pattern, f"[REDACTED_{label}]", redacted_text)
        return redacted_text

    def has_clearance(self, user_role: UserClearance, required_role: UserClearance) -> bool:
        """Check if user role meets or exceeds required clearance."""
        return self.CLEARANCE_LEVELS.get(user_role, 0) >= self.CLEARANCE_LEVELS.get(required_role, 0)

    def apply_security_governance(
        self,
        nodes: List[CandidateNode],
        user_role: UserClearance,
    ) -> Tuple[List[CandidateNode], Dict[str, Any]]:
        """Apply Tier 1 Domain Pruning and Tier 2 Token Masking.
        Returns:
            (filtered_nodes, security_audit_report)
        """
        governed_nodes: List[CandidateNode] = []
        pruned_nodes_count = 0
        masked_nodes_count = 0
        pruned_significant_variance = False

        dollar_pattern = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?")

        for node in nodes:
            # Check Clearance
            user_has_access = self.has_clearance(user_role, node.clearance_required)

            if not user_has_access:
                if node.security_tier == SecurityTier.TIER_1_DOMAIN_PRUNING:
                    # Tier 1: Domain-Level Pruning (Strategic Secrets)
                    # Node is completely dropped
                    pruned_nodes_count += 1
                    # If this node represents a major variance driver (> 30% contribution)
                    if node.raw_metric_values.get("margin_impact_pct", 0) <= -2.0 or \
                       node.raw_metric_values.get("drop_contrib", 0) >= 0.40:
                        pruned_significant_variance = True
                    continue

                elif node.security_tier == SecurityTier.TIER_2_TOKEN_MASKING:
                    # Tier 2: Token-Level Masking (Operational Confidentiality)
                    # Keep node in graph for math, mask confidential dollar values in content
                    masked_node = node.model_copy(deep=True)
                    masked_node.content = self._redact_pii(dollar_pattern.sub("<REDACTED_DOLLAR_VALUE>", node.content))
                    masked_node.title = self._redact_pii(dollar_pattern.sub("<REDACTED_DOLLAR_VALUE>", node.title))
                    masked_node.is_masked = True
                    masked_nodes_count += 1
                    governed_nodes.append(masked_node)
                    continue

            # Cleared node or Public node
            node.content = self._redact_pii(node.content)
            node.title = self._redact_pii(node.title)
            governed_nodes.append(node)

        audit_report = {
            "user_role": user_role.value,
            "pruned_nodes_count": pruned_nodes_count,
            "masked_nodes_count": masked_nodes_count,
            "pruned_significant_variance": pruned_significant_variance,
            "abstain_recommended": pruned_significant_variance,
            "abstain_reason": (
                "Insufficient authorized evidence: Primary causal driver pruned under Tier 1 Strategic Security Policy."
                if pruned_significant_variance else None
            ),
        }

        return governed_nodes, audit_report
