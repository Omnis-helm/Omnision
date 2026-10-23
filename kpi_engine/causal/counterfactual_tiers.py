"""
Counterfactual Impact Hierarchy: Tier 1 (Gold DAG Math), Tier 2 (Silver DiD), Tier 3 (Bronze CI) (§2.5.2, §5.3)
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np

from kpi_engine.data.models import AnchorNode, CandidateNode


class CounterfactualHierarchy:
    """Calculates non-ML and guarded counterfactual impact for candidate nodes."""

    @staticmethod
    def calculate_tier_1_multivariate_dag(
        p_base: float,
        v_base: float,
        delta_p: float,
        delta_v: float,
    ) -> Dict[str, float]:
        """Tier 1 (Gold) Math Expansion: ΔR = P*ΔV + V*ΔP + ΔP*ΔV.
        Returns exact dollar attribution for Price, Volume, and Joint Interaction.
        """
        price_effect = v_base * delta_p
        volume_effect = p_base * delta_v
        interaction_effect = delta_p * delta_v
        total_delta_r = price_effect + volume_effect + interaction_effect

        return {
            "price_effect_usd": round(price_effect, 2),
            "volume_effect_usd": round(volume_effect, 2),
            "interaction_effect_usd": round(interaction_effect, 2),
            "total_delta_r_usd": round(total_delta_r, 2),
            "price_attribution_pct": round((price_effect / total_delta_r) * 100.0, 2) if total_delta_r != 0 else 0.0,
            "volume_attribution_pct": round((volume_effect / total_delta_r) * 100.0, 2) if total_delta_r != 0 else 0.0,
            "interaction_attribution_pct": round((interaction_effect / total_delta_r) * 100.0, 2) if total_delta_r != 0 else 0.0,
        }

    @staticmethod
    def calculate_tier_2_did(
        affected_pre: float,
        affected_post: float,
        control_pre: float,
        control_post: float,
    ) -> Tuple[float, float]:
        """Tier 2 (Silver): Difference-in-Differences.
        DiD = (Y_affected_post - Y_affected_pre) - (Y_control_post - Y_control_pre)
        Returns: (did_effect, did_weight)
        """
        delta_affected = affected_post - affected_pre
        delta_control = control_post - control_pre
        did_effect = delta_affected - delta_control

        # Weight proportional to divergence from control
        normalized_div = abs(did_effect) / max(0.001, affected_pre)
        did_weight = min(1.0, max(0.0, normalized_div * 5.0))
        return round(did_effect, 4), round(did_weight, 4)

    @staticmethod
    def calculate_tier_3_ci_band(
        actual_val: float,
        mean_val: float,
        std_val: float,
        ci_level: float = 1.96,  # 95% CI
    ) -> Tuple[bool, float]:
        """Tier 3 (Bronze): 95% Confidence Interval Band.
        If actual falls inside [mean - 1.96*std, mean + 1.96*std], assign 0% weight.
        If pierces boundary, assign weight proportional to excess shock.
        """
        lower_bound = mean_val - ci_level * std_val
        upper_bound = mean_val + ci_level * std_val

        if lower_bound <= actual_val <= upper_bound:
            # Inside the 95% CI noise band => 0% causal weight
            return False, 0.0

        # Pierced the boundary!
        distance_outside = min(abs(actual_val - lower_bound), abs(actual_val - upper_bound))
        shock_weight = min(1.0, distance_outside / (2.0 * std_val))
        return True, round(shock_weight, 4)

    @staticmethod
    def calculate_metric_tree_share(anchor: AnchorNode, impact: float) -> float:
        """Share of the anchor's observed delta explained by a node's quantified impact (same units)."""
        anchor_delta = anchor.current_value - anchor.baseline_mean
        if anchor_delta == 0 or impact == 0 or (impact > 0) != (anchor_delta > 0):
            return 0.0
        return min(1.0, abs(impact) / abs(anchor_delta))

    def evaluate_node_counterfactual(
        self,
        anchor: AnchorNode,
        node: CandidateNode,
        context: Dict[str, Any],
    ) -> Tuple[float, str, Dict[str, Any]]:
        """Determines the appropriate tier and calculates Wcf.
        Returns: (Wcf_weight, tier_name, details_dict)
        """
        raw = node.raw_metric_values

        # Tier 1 Gold: explicit, deterministic contribution measured by the source system
        if "drop_contrib" in raw:
            contrib = raw["drop_contrib"]
            if contrib <= 0.0:
                return 0.0, "Tier 1 (Gold) — Non-causal (0 contribution)", {"drop_contribution": 0.0}
            return min(1.0, max(0.0, contrib)), "Tier 1 (Gold) — Deterministic System Log", {"drop_contribution": contrib}

        # Tier 1 Gold: multivariate metric tree ΔR = PΔV + VΔP + ΔPΔV (interaction split 50/50, Shapley-fair)
        if "delta_p" in raw or "delta_v" in raw:
            p_base = raw.get("p_base", context.get("p_base", 100.0))
            v_base = raw.get("v_base", context.get("v_base", 3500.0))
            delta_p = raw.get("delta_p", context.get("delta_p", 0.0))
            delta_v = raw.get("delta_v", context.get("delta_v", 0.0))

            dag_math = self.calculate_tier_1_multivariate_dag(p_base, v_base, delta_p, delta_v)
            total = dag_math["total_delta_r_usd"]
            if total == 0:
                return 0.0, "Tier 1 (Gold) — Multivariate DAG", dag_math
            if node.metadata.get("driver_type") == "price_change":
                own = dag_math["price_effect_usd"] + 0.5 * dag_math["interaction_effect_usd"]
            else:
                own = dag_math["volume_effect_usd"] + 0.5 * dag_math["interaction_effect_usd"]
            w_cf = abs(own) / abs(total)
            dag_math["node_attributed_usd"] = round(own, 2)
            return min(1.0, max(0.0, w_cf)), "Tier 1 (Gold) — Multivariate DAG", dag_math

        # Tier 1 Gold: metric-tree decomposition in the anchor's own units (e.g. margin points)
        for key in ("anchor_impact", "margin_impact_pct"):
            if key in raw:
                share = self.calculate_metric_tree_share(anchor, raw[key])
                return share, "Tier 1 (Gold) — Metric-Tree Decomposition", {
                    "impact": raw[key],
                    "anchor_delta": round(anchor.current_value - anchor.baseline_mean, 4),
                    "explained_share": round(share, 4),
                }

        # Tier 2 Silver: Difference-in-Differences against a parallel control cohort
        if "control_pre" in context and "control_post" in context:
            did_effect, did_weight = self.calculate_tier_2_did(
                affected_pre=anchor.baseline_mean,
                affected_post=anchor.current_value,
                control_pre=context["control_pre"],
                control_post=context["control_post"],
            )
            return did_weight, "Tier 2 (Silver) — Difference-in-Differences", {"did_effect": did_effect}

        # Tier 3 Bronze: the anomaly is real (CI band pierced) but this node's share is unquantified,
        # so it only receives half of the shock weight.
        is_breach, ci_weight = self.calculate_tier_3_ci_band(
            actual_val=anchor.current_value,
            mean_val=anchor.baseline_mean,
            std_val=anchor.baseline_std,
        )
        return round(0.5 * ci_weight, 4), "Tier 3 (Bronze) — Confidence Interval Bands (node impact unquantified)", {
            "ci_breach": is_breach, "shock_weight": ci_weight}
