"""
Master Composite Causal Scorer & Context Pre-Sorter (§2.5, §2.6, §5.4, §6.1)

W(A*, n_i) = CR * CI
  CR: contextual relevance (temporal, entity, semantic)
  CI: delta*Wsnr + epsilon*Wcf, collapsing to 0 when the counterfactual proves zero contribution

Historical precedents retrieved from institutional memory are scored separately: they are
supporting context (or a noise signature), never a causal driver of today's anomaly.
"""

from typing import List, Tuple, Dict, Any, Optional, Set

from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType
from kpi_engine.causal.contextual_relevance import ContextualRelevanceScorer
from kpi_engine.causal.counterfactual_tiers import CounterfactualHierarchy
from kpi_engine.causal.shapley_engine import ShapleyCausalEngine
from kpi_engine.config import CONFIG

HISTORICAL_TYPES = (CandidateNodeType.HISTORICAL_PRECEDENT, CandidateNodeType.HISTORICAL_NOISE)

# driver_type on evidence nodes -> feature name in the global ML model
AMBIENT_FEATURE_MAP = {
    "ambient_competitor": "competitor_price",
    "ambient_weather": "weather_severity",
    "ambient_latency": "server_latency",
    "ambient_marketing": "marketing_spend",
}

ScoredNode = Tuple[CandidateNode, float, float, float, str, Dict[str, Any]]


def is_historical(node: CandidateNode) -> bool:
    return node.node_type in HISTORICAL_TYPES


class CompositeCausalScorer:
    """Calculates multiplicative composite causal weights and sorts context to prevent 'Lost in the Middle'."""

    def __init__(self, config=CONFIG, cr_scorer: Optional[ContextualRelevanceScorer] = None):
        self.config = config
        self.cr_scorer = cr_scorer or ContextualRelevanceScorer(config)
        self.cf_hierarchy = CounterfactualHierarchy()
        self.shap_engine = ShapleyCausalEngine()

    @staticmethod
    def compute_snr_weight(anchor: AnchorNode) -> float:
        """Signal-to-Noise Ratio (Wsnr): Z/5 clipped to [0, 1] (Z >= 5 is a full shock)."""
        return min(1.0, max(0.0, anchor.z_score / 5.0))

    def _score_historical(self, anchor: AnchorNode, node: CandidateNode, w_snr: float):
        sim = float(node.metadata.get("similarity_score", 0.0))
        cross = node.metadata.get("is_cross_regional", False)
        if node.node_type == CandidateNodeType.HISTORICAL_NOISE:
            w_cf = 0.0 if cross else 1.0
            tier = ("Context — Cross-Regional Noise Signature (ignored)" if cross
                    else "Context — Known Noise Signature (false-alarm check)")
        else:
            w_cf = self.config.history_precedent_wcf_cross_region if cross else self.config.history_precedent_wcf_local
            tier = ("Context — Cross-Regional Historical Precedent" if cross
                    else "Context — Verified Historical Precedent (Vector-RAG)")
        cr = sim
        ci = 0.0 if w_cf == 0 else min(1.0, self.config.delta_wsnr * w_snr + self.config.epsilon_wcf * w_cf)
        details = {"vector_similarity": sim, "is_cross_regional": cross, "historical_id": node.metadata.get("historical_id"),
                   "is_historical": True, "is_noise": node.node_type == CandidateNodeType.HISTORICAL_NOISE}
        return cr, ci, tier, details

    def score_candidate_nodes(
        self,
        anchor: AnchorNode,
        nodes: List[CandidateNode],
        context: Dict[str, Any],
        global_model=None,
        anomaly_row=None,
        demoted_node_ids: Optional[Set[str]] = None,
    ) -> List[ScoredNode]:
        """Returns (node, W, CR, CI, tier, details) sorted descending by W, causal drivers before history."""
        demoted_node_ids = demoted_node_ids or set()
        scored_results: List[ScoredNode] = []
        w_snr = self.compute_snr_weight(anchor)

        # SHAP attribution for ambient variables (computed once per run)
        shap_data = None
        has_ambient = any(n.metadata.get("driver_type") in AMBIENT_FEATURE_MAP for n in nodes)
        if has_ambient and global_model is not None and anomaly_row is not None:
            shap_data = self.shap_engine.evaluate_with_global_model(global_model, anomaly_row)
            context["shap_attribution"] = shap_data
        anomaly_sign = -1.0 if anchor.variance_pct < 0 else 1.0

        for node in nodes:
            if is_historical(node):
                cr, ci, tier_str, cf_details = self._score_historical(anchor, node, w_snr)
                scored_results.append((node, round(cr * ci, 4), round(cr, 4), round(ci, 4), tier_str, cf_details))
                continue

            cr_parts = self.cr_scorer.calculate_cr_components(anchor, node)
            cr = cr_parts["CR"]

            driver_type = node.metadata.get("driver_type")
            if driver_type in AMBIENT_FEATURE_MAP and shap_data:
                feat = AMBIENT_FEATURE_MAP[driver_type]
                signed_share = shap_data["relative_attribution"].get(feat, 0.0)
                # Only a feature pushing the KPI in the anomaly's direction explains the anomaly
                w_cf = abs(signed_share) if signed_share * anomaly_sign > 0 else 0.0
                tier_str = "Tier 3 (Bronze) — SHAP Cooperative Game (global model)"
                cf_details = {"feature": feat, "signed_share": round(signed_share, 4),
                              "shap_value": shap_data["shap_values"].get(feat), "model": shap_data.get("model_type")}
            else:
                w_cf, tier_str, cf_details = self.cf_hierarchy.evaluate_node_counterfactual(anchor, node, context)

            ci = 0.0 if w_cf == 0.0 else min(1.0, max(0.0, self.config.delta_wsnr * w_snr + self.config.epsilon_wcf * w_cf))
            composite_w = cr * ci

            cf_details = {**cf_details, "w_cf": round(w_cf, 4), "w_snr": round(w_snr, 4), **cr_parts}
            if node.node_id in demoted_node_ids:
                composite_w *= self.config.demotion_penalty
                cf_details["human_demoted"] = True
                tier_str += " · demoted by analyst"

            scored_results.append((node, round(composite_w, 4), round(cr, 4), round(ci, 4), tier_str, cf_details))

        # Context sorting (§6.1): causal drivers first, by W descending; history after.
        return sorted(scored_results, key=lambda item: (is_historical(item[0]), -item[1]))
