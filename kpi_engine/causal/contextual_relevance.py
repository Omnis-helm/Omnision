"""
Contextual Relevance Gatekeeper (§2.5.1, §5.1)
"""

import math
import re
from typing import Dict, Any, List
from datetime import datetime

from kpi_engine.data.models import AnchorNode, CandidateNode
from kpi_engine.config import CONFIG


class ContextualRelevanceScorer:
    """Evaluates whether an evidence node contextually relates to the anchor anomaly."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.semantic_threshold = 0.20  # Base threshold, tunable via recalibration

    def compute_temporal_proximity(self, anchor_time: datetime, node_time: datetime) -> float:
        """Temporal Proximity (Wt): Exponential decay based on time difference in hours."""
        delta_hours = abs((anchor_time - node_time).total_seconds()) / 3600.0
        # Decay factor: drops to ~0.50 at 24 hours, ~0.85 at 4 hours
        wt = math.exp(-0.03 * delta_hours)
        return min(1.0, max(0.0, wt))

    def compute_entity_overlap(
        self, anchor_dims: Dict[str, str], node_dims: Dict[str, str]
    ) -> float:
        """Entity Overlap (We): Matching rate of metadata tags (region, platform, sku, system)."""
        if not anchor_dims:
            return 0.5

        matches = 0
        total_checks = 0

        for key, anchor_val in anchor_dims.items():
            if key in node_dims:
                total_checks += 1
                node_val = node_dims[key]
                if str(anchor_val).lower() == str(node_val).lower() or node_val.lower() in ["all", "global"]:
                    matches += 1

        if total_checks == 0:
            return 0.40  # Neutral overlap if distinct dimension keys
        return matches / total_checks

    def compute_semantic_distance(self, anchor_text: str, node_text: str) -> float:
        """Semantic Distance (Ws): Cosine word-overlap similarity."""
        def tokenize(text: str) -> set:
            words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", text.lower())
            # filter stop words
            stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was"}
            return {w for w in words if w not in stopwords}

        tokens_anchor = tokenize(anchor_text)
        tokens_node = tokenize(node_text)

        if not tokens_anchor or not tokens_node:
            return 0.0

        intersection = tokens_anchor.intersection(tokens_node)
        union = tokens_anchor.union(tokens_node)

        # Jaccard / Cosine overlap index
        jaccard = len(intersection) / len(union) if union else 0.0

        # Keyword boost for technical / causal terms
        causal_keywords = {"timeout", "latency", "error", "failed", "outage", "spike", "drop", "discount", "tariff"}
        boost = 0.25 if any(k in tokens_node for k in causal_keywords) else 0.0

        return min(1.0, max(0.0, jaccard + boost))

    def calculate_cr(
        self,
        anchor: AnchorNode,
        node: CandidateNode,
    ) -> float:
        """Computes composite Contextual Relevance: CR = alpha*Wt + beta*We + gamma*Ws."""
        anchor_desc = f"{anchor.metric_name} {anchor.trigger_rule} {' '.join(f'{k}:{v}' for k, v in anchor.dimensions.items())}"
        node_desc = f"{node.title} {node.content} {' '.join(f'{k}:{v}' for k, v in node.dimensions.items())}"

        wt = self.compute_temporal_proximity(anchor.timestamp, node.timestamp)
        we = self.compute_entity_overlap(anchor.dimensions, node.dimensions)
        ws = self.compute_semantic_distance(anchor_desc, node_desc)

        cr = (
            self.config.alpha_wt * wt
            + self.config.beta_we * we
            + self.config.gamma_ws * ws
        )
        return min(1.0, max(0.0, cr))
