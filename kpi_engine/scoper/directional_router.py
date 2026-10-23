"""
Directional Scoping & Dynamic Scope Expansion Router (§2.3, §3.1)

Decides where along the value chain to look for causes (upstream supply / midstream operations /
downstream demand) and removes evidence that sits on the opposite side of the chain.
"""

from typing import List, Dict, Any
from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType


# Value-chain layers searched for each direction
DIRECTION_LAYERS = {
    "upstream": {"upstream", "macro", "financials"},
    "downstream": {"downstream", "macro", "financials"},
    "midstream": {"midstream", "financials"},
}

# Node types that are always relevant for a direction even without a `layer` tag
DIRECTION_TYPES = {
    "upstream": {
        CandidateNodeType.SUPPLIER_NOTICE,
        CandidateNodeType.MACRO_INDICATOR,
        CandidateNodeType.EXECUTIVE_STRATEGIC,
    },
    "downstream": {
        CandidateNodeType.SYSTEM_LOG,
        CandidateNodeType.SUPPORT_TICKET_CLUSTER,
        CandidateNodeType.MARKETING_LOG,
        CandidateNodeType.COMPETITOR_ACTION,
        CandidateNodeType.MACRO_INDICATOR,
        CandidateNodeType.EXECUTIVE_STRATEGIC,
    },
    "midstream": {
        CandidateNodeType.OPERATIONAL_LOG,
        CandidateNodeType.SYSTEM_LOG,
    },
}


class DirectionalScoper:
    """Routes the search scope along the value chain based on variance decomposition."""

    @staticmethod
    def determine_direction(anchor: AnchorNode, context: Dict[str, Any]) -> str:
        """Determines if the anomaly points Upstream, Downstream, Midstream, or All."""
        cogs_moved = context.get("cogs_moved", False)
        ltv_moved = context.get("ltv_moved", False)

        if cogs_moved and not ltv_moved:
            return "upstream"
        if ltv_moved and not cogs_moved:
            return "downstream"

        domain = anchor.dimensions.get("domain", "").lower()
        metric_name = anchor.metric_name.lower()

        if "cogs" in metric_name or "procurement" in metric_name or domain == "upstream":
            return "upstream"
        if "conversion" in metric_name or "ltv" in metric_name or "checkout" in metric_name or domain == "downstream":
            return "downstream"
        if "factory" in metric_name or "production" in metric_name or domain == "midstream":
            return "midstream"
        return "all"

    def filter_by_direction(
        self,
        anchor: AnchorNode,
        evidence_pool: List[CandidateNode],
        context: Dict[str, Any],
    ) -> List[CandidateNode]:
        """Keep evidence on the searched side of the value chain.

        A node is kept when its `layer` tag is in scope, or (when it carries no layer tag) when its
        node type is relevant for the direction. Nodes explicitly tagged with an out-of-scope layer
        are dropped.
        """
        direction = self.determine_direction(anchor, context)
        context["scope_direction"] = direction
        if direction == "all":
            return list(evidence_pool)

        layers = DIRECTION_LAYERS[direction]
        types = DIRECTION_TYPES[direction]
        filtered_nodes = []
        for node in evidence_pool:
            layer = str(node.metadata.get("layer", "")).lower()
            if layer:
                if layer in layers:
                    filtered_nodes.append(node)
            elif node.node_type in types:
                filtered_nodes.append(node)
        return filtered_nodes
