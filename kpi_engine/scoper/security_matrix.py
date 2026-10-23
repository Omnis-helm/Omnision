"""
Hybrid Security Matrix: Tier 1 Domain Pruning & Tier 2 Token Masking (§2.3, §4.3)

* Tier 1 (strategic secrets, e.g. M&A): node is removed for users below its clearance. If the removed
  node was a major variance driver the engine abstains instead of presenting an incomplete story.
* Tier 2 (operational confidentiality): node stays in the graph (its numbers still feed the math) but
  dollar values / PII are masked in the text shown to the user.
* Independently of the user's clearance, Tier 2 text is always masked before it is sent to a public
  cloud LLM (OpenAI / Anthropic / Gemini). See `mask_for_external_llm`.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any

from kpi_engine.data.models import (
    CandidateNode,
    SecurityTier,
    UserClearance,
)

CLEARANCE_LEVELS = {
    UserClearance.PUBLIC: 0,
    UserClearance.JUNIOR_ANALYST: 1,
    UserClearance.SENIOR_ENGINEER: 2,
    UserClearance.EXECUTIVE_VP: 3,
    UserClearance.ADMIN: 4,
}


def clearance_level(role: UserClearance) -> int:
    return CLEARANCE_LEVELS.get(role, 0)


class HybridSecurityMatrix:
    """Applies role-based access control without corrupting causal diagnostic math."""

    CLEARANCE_LEVELS = CLEARANCE_LEVELS

    PII_PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "CREDIT_CARD": r"\b(?:\d[ -]?){13,16}\b",
    }
    DOLLAR_PATTERN = re.compile(r"\$\s?\d+(?:,\d{3})*(?:\.\d+)?(?:\s?(?:k|K|m|M|bn|million|billion))?")

    # A pruned Tier-1 node is "significant" if it explains this much of the anomaly
    SIGNIFICANT_DROP_CONTRIB = 0.40
    SIGNIFICANT_MARGIN_IMPACT_PCT = -2.0

    def _redact_pii(self, text: str) -> str:
        redacted_text = text
        for label, pattern in self.PII_PATTERNS.items():
            redacted_text = re.sub(pattern, f"[REDACTED_{label}]", redacted_text)
        return redacted_text

    def _mask_text(self, text: str) -> str:
        return self._redact_pii(self.DOLLAR_PATTERN.sub("<REDACTED_DOLLAR_VALUE>", text))

    def has_clearance(self, user_role: UserClearance, required_role: UserClearance) -> bool:
        return clearance_level(user_role) >= clearance_level(required_role)

    def _is_significant(self, node: CandidateNode) -> bool:
        raw = node.raw_metric_values
        return (
            raw.get("margin_impact_pct", 0.0) <= self.SIGNIFICANT_MARGIN_IMPACT_PCT
            or raw.get("drop_contrib", 0.0) >= self.SIGNIFICANT_DROP_CONTRIB
        )

    def mask_node(self, node: CandidateNode) -> CandidateNode:
        masked = node.model_copy(deep=True)
        masked.content = self._mask_text(node.content)
        masked.title = self._mask_text(node.title)
        masked.is_masked = True
        return masked

    def apply_security_governance(
        self,
        nodes: List[CandidateNode],
        user_role: UserClearance,
    ) -> Tuple[List[CandidateNode], Dict[str, Any]]:
        """Apply Tier 1 Domain Pruning and Tier 2 Token Masking.
        Returns (governed_nodes, security_audit_report). Input nodes are never mutated.
        """
        governed_nodes: List[CandidateNode] = []
        pruned_ids: List[str] = []
        masked_ids: List[str] = []
        pruned_significant_variance = False

        for node in nodes:
            user_has_access = self.has_clearance(user_role, node.clearance_required)

            if not user_has_access and node.security_tier == SecurityTier.TIER_1_DOMAIN_PRUNING:
                pruned_ids.append(node.node_id)
                if self._is_significant(node):
                    pruned_significant_variance = True
                continue

            if not user_has_access and node.security_tier == SecurityTier.TIER_2_TOKEN_MASKING:
                governed_nodes.append(self.mask_node(node))
                masked_ids.append(node.node_id)
                continue

            if not user_has_access:
                # Public tier but clearance mismatch: treat like Tier 2 (never leak raw text)
                governed_nodes.append(self.mask_node(node))
                masked_ids.append(node.node_id)
                continue

            cleared = node.model_copy(deep=True)
            cleared.content = self._redact_pii(cleared.content)
            cleared.title = self._redact_pii(cleared.title)
            governed_nodes.append(cleared)

        audit_report: Dict[str, Any] = {
            "user_role": user_role.value,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "evaluated_nodes_count": len(nodes),
            "pruned_nodes_count": len(pruned_ids),
            "masked_nodes_count": len(masked_ids),
            "masked_node_ids": masked_ids,
            "pruned_significant_variance": pruned_significant_variance,
            "abstain_recommended": pruned_significant_variance,
            "abstain_reason": (
                "Insufficient authorized evidence: Primary causal driver pruned under Tier 1 Strategic Security Policy."
                if pruned_significant_variance else None
            ),
        }
        # Tamper-evident receipt. Pruned node ids are hashed into the receipt, not listed in clear.
        receipt_material = json.dumps({**audit_report, "pruned_node_ids": sorted(pruned_ids)}, sort_keys=True)
        audit_report["audit_receipt_sha256"] = hashlib.sha256(receipt_material.encode("utf-8")).hexdigest()
        return governed_nodes, audit_report

    def mask_for_external_llm(self, nodes: List[CandidateNode]) -> List[CandidateNode]:
        """Mask Tier-2 nodes before evidence leaves the trust boundary (public cloud LLM)."""
        out = []
        for n in nodes:
            if n.security_tier == SecurityTier.TIER_2_TOKEN_MASKING and not n.is_masked:
                out.append(self.mask_node(n))
            elif n.security_tier == SecurityTier.TIER_1_DOMAIN_PRUNING:
                # Strategic secrets never go to a third-party model verbatim
                out.append(self.mask_node(n))
            else:
                out.append(n)
        return out
