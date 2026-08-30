"""
Directional Scoping & Dynamic Scope Expansion Router (§2.3, §3.1)
"""

from typing import List, Dict, Any, Set
from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType


class DirectionalScoper:
    """Routes the search scope along the value chain based on variance decomposition."""

    @staticmethod
    def determine_direction(anchor: AnchorNode, context: Dict[str, Any]) -> str:
        """Determines if the anomaly points Upstream, Downstream, Midstream, or Macro."""
        # 1. Check explicit variance decomposition in context
        cogs_moved = context.get("cogs_moved", False)
        ltv_moved = context.get("ltv_moved", False)

        if cogs_moved and not ltv_moved:
            return "upstream"
        elif ltv_moved and not cogs_moved:
            return "downstream"

        # 2. Check anchor KPI domain & name heuristics
        domain = anchor.dimensions.get("domain", "").lower()
        metric_name = anchor.metric_name.lower()

        if "cogs" in metric_name or "procurement" in metric_name or domain == "upstream":
            return "upstream"
        if "conversion" in metric_name or "ltv" in metric_name or "checkout" in metric_name or domain == "downstream":
            return "downstream"
        if "factory" in metric_name or "production" in metric_name or domain == "midstream":
            return "midstream"

        # Default fallback
        return "all"

    def filter_by_direction(
        self,
        anchor: AnchorNode,
        evidence_pool: List[CandidateNode],
        context: Dict[str, Any],
    ) -> List[CandidateNode]:
        """Filter candidate evidence pool according to directional value-chain scope."""
        direction = self.determine_direction(anchor, context)

        if direction == "all":
            return evidence_pool

        filtered_nodes = []
        for node in evidence_pool:
            layer = node.metadata.get("layer", "").lower()
            node_type = node.node_type

            if direction == "upstream":
                # Keep upstream, macro, financials; drop purely downstream customer tickets
                if layer in ["upstream", "macro", "financials"] or node_type in [
                    CandidateNodeType.SUPPLIER_NOTICE,
                    CandidateNodeType.MACRO_INDICATOR,
                    CandidateNodeType.EXECUTIVE_STRATEGIC,
                ]:
                    filtered_nodes.append(node)

            elif direction == "downstream":
                # Keep downstream, financials, macro; drop midstream factory logs or raw material notices
                if layer in ["downstream", "macro", "financials"] or node_type in [
                    CandidateNodeType.SYSTEM_LOG,
                    CandidateNodeType.SUPPORT_TICKET_CLUSTER,
                    CandidateNodeType.MARKETING_LOG,
                    CandidateNodeType.COMPETITOR_ACTION,
                    CandidateNodeType.EXECUTIVE_STRATEGIC,
                ]:
                    filtered_nodes.append(node)

            elif direction == "midstream":
                if layer in ["midstream", "financials"] or node_type in [
                    CandidateNodeType.OPERATIONAL_LOG,
                    CandidateNodeType.SYSTEM_LOG,
                ]:
                    filtered_nodes.append(node)

        return filtered_nodes
