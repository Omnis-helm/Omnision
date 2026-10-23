"""
Contextual Relevance Gatekeeper (§2.5.1, §5.1)

CR = alpha*Wt + beta*We + gamma*Ws
  Wt  temporal proximity (exponential decay on hours between anchor and evidence)
  We  entity overlap (shared dimension tags such as region / platform / category)
  Ws  semantic similarity of anchor description vs evidence text. Values below the
      (human-recalibrated) semantic threshold are treated as 0.
"""

import math
from datetime import datetime
from typing import Dict

from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.config import CONFIG
from kpi_engine.ml.local_ml_engine import semantic_similarity, tokenize

CAUSAL_SIGNAL_TERMS = {
    "latency", "error", "fail", "failure", "outage", "spike", "drop", "promotion", "tariff", "fee",
    "breach", "regression", "crash", "ban", "heatwave", "shortage", "auth",
}


class ContextualRelevanceScorer:
    """Evaluates whether an evidence node contextually relates to the anchor anomaly."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.semantic_threshold = config.semantic_threshold_initial

    @staticmethod
    def compute_temporal_proximity(anchor_time: datetime, node_time: datetime) -> float:
        """Wt = exp(-0.03 * |Δhours|): ~0.89 at 4h, ~0.49 at 24h, ~0.24 at 48h."""
        delta_hours = abs((anchor_time - node_time).total_seconds()) / 3600.0
        return min(1.0, max(0.0, math.exp(-0.03 * delta_hours)))

    @staticmethod
    def compute_entity_overlap(anchor_dims: Dict[str, str], node_dims: Dict[str, str]) -> float:
        """We: share of comparable dimension keys whose values match ('all'/'global' match anything)."""
        if not anchor_dims:
            return 0.5
        matches = 0
        total_checks = 0
        for key, anchor_val in anchor_dims.items():
            if key == "domain" or key not in node_dims:
                continue
            total_checks += 1
            node_val = str(node_dims[key]).lower()
            if str(anchor_val).lower() == node_val or node_val in ("all", "global"):
                matches += 1
        if total_checks == 0:
            return 0.40  # neutral when no comparable tags
        return matches / total_checks

    def compute_semantic_distance(self, anchor_text: str, node_text: str) -> float:
        """Ws: semantic similarity plus a small boost when the evidence describes a causal signal."""
        sim = semantic_similarity(anchor_text, node_text)
        boost = 0.25 if CAUSAL_SIGNAL_TERMS & set(tokenize(node_text)) else 0.0
        ws = min(1.0, sim + boost)
        return ws if ws >= self.semantic_threshold else 0.0

    def calculate_cr_components(self, anchor: AnchorNode, node: CandidateNode) -> Dict[str, float]:
        anchor_desc = f"{anchor.metric_name} {' '.join(str(v) for v in anchor.dimensions.values())}"
        node_desc = f"{node.title} {node.content} {' '.join(str(v) for v in node.dimensions.values())}"
        wt = self.compute_temporal_proximity(anchor.timestamp, node.timestamp)
        we = self.compute_entity_overlap(anchor.dimensions, node.dimensions)
        ws = self.compute_semantic_distance(anchor_desc, node_desc)
        cr = self.config.alpha_wt * wt + self.config.beta_we * we + self.config.gamma_ws * ws
        return {"Wt": round(wt, 4), "We": round(we, 4), "Ws": round(ws, 4), "CR": round(min(1.0, max(0.0, cr)), 4)}

    def calculate_cr(self, anchor: AnchorNode, node: CandidateNode) -> float:
        return self.calculate_cr_components(anchor, node)["CR"]
