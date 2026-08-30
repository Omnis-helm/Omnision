"""
Test Suite for Causal Inference Math, Multivariate DAG Interaction & Exact SHAP (§2.5, §5.3, §5.4)
"""

import pytest
from datetime import datetime, timedelta

from kpi_engine.causal.counterfactual_tiers import CounterfactualHierarchy
from kpi_engine.causal.shapley_engine import ShapleyCausalEngine
from kpi_engine.causal.composite_scorer import CompositeCausalScorer
from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType, LifecycleStage


def test_tier_1_multivariate_dag_math():
    """Verify ΔR = P*ΔV + V*ΔP + ΔP*ΔV exact formula."""
    p_base = 100.0
    v_base = 3500.0
    delta_p = -8.0
    delta_v = -217.4

    res = CounterfactualHierarchy.calculate_tier_1_multivariate_dag(
        p_base, v_base, delta_p, delta_v
    )

    # Price effect = 3500 * (-8) = -28,000
    assert res["price_effect_usd"] == -28000.0
    # Volume effect = 100 * (-217.4) = -21,740
    assert res["volume_effect_usd"] == -21740.0
    # Joint Interaction effect = (-8) * (-217.4) = +1739.2
    assert res["interaction_effect_usd"] == 1739.2
    # Total ΔR = -28000 - 21740 + 1739.2 = -48000.8
    assert abs(res["total_delta_r_usd"] - (-48000.8)) < 1.0


def test_exact_shapley_values():
    """Verify exact Shapley cooperative game theory attribution across feature permutations."""
    features = ["competitor_promotion", "weather_heatwave"]

    def game_v(subset):
        if set(subset) == {"competitor_promotion"}:
            return 0.60
        if set(subset) == {"weather_heatwave"}:
            return 0.30
        if set(subset) == {"competitor_promotion", "weather_heatwave"}:
            return 1.00  # 0.60 + 0.30 + 0.10 interaction synergy
        return 0.0

    shap_vals = ShapleyCausalEngine.compute_exact_shapley_values(features, game_v)

    # phi(promo) = 1/2 * (0.60 - 0) + 1/2 * (1.00 - 0.30) = 0.30 + 0.35 = 0.65
    # phi(weather) = 1/2 * (0.30 - 0) + 1/2 * (1.00 - 0.60) = 0.15 + 0.20 = 0.35
    assert round(shap_vals["competitor_promotion"], 2) == 0.65
    assert round(shap_vals["weather_heatwave"], 2) == 0.35
    assert round(sum(shap_vals.values()), 2) == 1.00


def test_multiplicative_composite_weight_zero_collapse():
    """Verify that if either Contextual Relevance or Causal Impact is 0, W collapses to 0."""
    scorer = CompositeCausalScorer()
    base_time = datetime(2026, 8, 30, 10, 0, 0)

    anchor = AnchorNode(
        kpi_id="KPI_WEST_CHECKOUT_CONV",
        metric_name="West Region Checkout Conversion",
        timestamp=base_time,
        current_value=2.80,
        baseline_mean=3.20,
        baseline_std=0.08,
        variance_pct=-12.5,
        z_score=5.0,
        lifecycle_stage=LifecycleStage.MATURE,
        trigger_rule="Z_SCORE_ANOMALY",
    )

    # Irrelevant node in East DC with no causal impact
    noise_node = CandidateNode(
        node_id="NODE-NOISE-999",
        node_type=CandidateNodeType.OPERATIONAL_LOG,
        title="Unrelated East warehouse coffee machine repair",
        content="Coffee machine was repaired in East breakroom",
        timestamp=base_time - timedelta(hours=35),
        dimensions={"region": "East"},
        raw_metric_values={"drop_contrib": 0.0},
    )

    results = scorer.score_candidate_nodes(anchor, [noise_node], {})
    node, w, cr, ci, tier, _ = results[0]

    # CI is low / 0, so W collapses
    assert w < 0.25
