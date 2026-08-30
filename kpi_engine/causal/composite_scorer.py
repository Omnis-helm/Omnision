"""
Master Composite Causal Scorer & Context Pre-Sorter (§2.5, §2.6, §5.4, §6.1)
"""

from typing import List, Tuple, Dict, Any

from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType
from kpi_engine.causal.contextual_relevance import ContextualRelevanceScorer
from kpi_engine.causal.counterfactual_tiers import CounterfactualHierarchy
from kpi_engine.causal.shapley_engine import ShapleyCausalEngine
from kpi_engine.config import CONFIG


class CompositeCausalScorer:
    """Calculates multiplicative composite causal weights and sorts context to prevent 'Lost in the Middle'."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.cr_scorer = ContextualRelevanceScorer(config)
        self.cf_hierarchy = CounterfactualHierarchy()
        self.shap_engine = ShapleyCausalEngine()

    def compute_snr_weight(self, anchor: AnchorNode) -> float:
        """Signal-to-Noise Ratio (Wsnr) normalized against 30-day Z-score."""
        z = anchor.z_score
        # Z > 5.0 => shock 1.0, Z < 2.0 => noise < 0.40
        return min(1.0, max(0.0, z / 5.0))

    def score_candidate_nodes(
        self,
        anchor: AnchorNode,
        nodes: List[CandidateNode],
        context: Dict[str, Any],
        global_model=None,
        anomaly_row=None,
    ) -> List[Tuple[CandidateNode, float, float, float, str, Dict[str, Any]]]:
        """Calculates W(A*, n_i) = CR * CI for all candidate nodes.
        Returns:
            List of (node, composite_W, contextual_relevance, causal_impact, tier_str, details)
            sorted descending by composite_W.
        """
        scored_results = []
        w_snr = self.compute_snr_weight(anchor)

        # Check if scenario has ambient variables needing SHAP
        shap_ambient_data = None
        has_ambient = any(n.metadata.get("driver_type") in ["ambient_competitor", "ambient_weather"] for n in nodes)
        if has_ambient and global_model and anomaly_row is not None:
            shap_ambient_data = self.shap_engine.evaluate_with_global_model(
                global_model=global_model,
                anomaly_row=anomaly_row
            )

        for node in nodes:
            # 1. Compute Contextual Relevance (The Gatekeeper)
            if node.node_type in [CandidateNodeType.HISTORICAL_PRECEDENT, CandidateNodeType.HISTORICAL_NOISE]:
                # Bypass standard temporal checks, rely on FAISS vector similarity
                sim_score = float(node.dimensions.get("similarity", 1.0))
                # Map FAISS distance to a 0.7 - 0.99 CR score
                cr = max(0.7, 1.0 - (sim_score * 0.2)) 
            else:
                cr = self.cr_scorer.calculate_cr(anchor, node)

            # 2. Compute Counterfactual Impact (Wcf)
            driver_type = node.metadata.get("driver_type")
            is_cross_regional = node.metadata.get("is_cross_regional", False)
            
            if node.node_type == CandidateNodeType.HISTORICAL_PRECEDENT:
                if is_cross_regional:
                    w_cf = 0.60 # Tier 2 (Silver) Hypothesis
                    tier_str = f"Tier 2 (Silver) — Cross-Regional Hypothesis (from {node.metadata.get('historical_region')})"
                else:
                    w_cf = 0.95 # Highly causal due to being a verified local past incident
                    tier_str = "Tier 0 (Platinum) — Verified Historical Precedent via Vector-RAG"
                cf_details = {"vector_similarity": node.dimensions.get("similarity"), "is_cross_regional": is_cross_regional}
                
            elif node.node_type == CandidateNodeType.HISTORICAL_NOISE:
                if is_cross_regional:
                    w_cf = 0.40 # Drops below 0.65 prune threshold! Forces local investigation.
                    tier_str = f"Discarded — Cross-Regional Noise Hypothesis (from {node.metadata.get('historical_region')})"
                else:
                    w_cf = 1.00 # Force it to survive the brakes so LLM explicitly sees it's noise
                    tier_str = "Tier 0 (Platinum) — Verified Historical NOISE (False Alarm)"
                cf_details = {"vector_similarity": node.dimensions.get("similarity"), "is_noise": True, "is_cross_regional": is_cross_regional}
            elif driver_type in ["ambient_competitor", "ambient_weather"] and shap_ambient_data:
                feat_key = "competitor_promotion" if driver_type == "ambient_competitor" else "weather_heatwave"
                w_cf = shap_ambient_data["shapley_values"].get(feat_key, 0.20)
                tier_str = "Tier 3 (Bronze) — SHAP Cooperative Game"
                cf_details = {"shapley_attribution": shap_ambient_data}
            else:
                w_cf, tier_str, cf_details = self.cf_hierarchy.evaluate_node_counterfactual(
                    anchor, node, context
                )

            # 3. Blended Causal Impact: CI = delta*Wsnr + epsilon*Wcf
            # If counterfactual is 0 (i.e. proven zero damage), CI collapses to 0
            if w_cf == 0.0:
                ci = 0.0
            else:
                ci = self.config.delta_wsnr * w_snr + self.config.epsilon_wcf * w_cf
                ci = min(1.0, max(0.0, ci))

            # 4. Master Multiplicative Formula: W = CR * CI
            # (Multiplication ensures a node must have BOTH contextual match and mathematical causal impact!)
            composite_w = cr * ci

            scored_results.append((
                node,
                round(composite_w, 4),
                round(cr, 4),
                round(ci, 4),
                tier_str,
                cf_details,
            ))

        # Context Sorting (§6.1): Sort descending by composite weight W
        # Forces LLM's attention mechanism to anchor on strongest mathematical evidence first
        sorted_results = sorted(scored_results, key=lambda item: item[1], reverse=True)
        return sorted_results
