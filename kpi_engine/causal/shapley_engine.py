"""
Shapley Additive exPlanations (SHAP) Engine for Ambient / Interacting Variables (§2.5.3, §5.3.4)
"""

import itertools
import math
from typing import Dict, List, Callable, Any


class ShapleyCausalEngine:
    """Computes exact cooperative game theory Shapley attribution values across feature permutations."""

    @staticmethod
    def compute_exact_shapley_values(
        features: List[str],
        value_function: Callable[[List[str]], float],
    ) -> Dict[str, float]:
        """Calculates Shapley value for each feature across all 2^N feature coalitions.
        phi_i = sum_{S subset N \\ {i}} [ |S|! * (|N| - |S| - 1)! / |N|! ] * [ v(S U {i}) - v(S) ]
        """
        n = len(features)
        shapley_values: Dict[str, float] = {f: 0.0 for f in features}

        # Cache coalition values
        coalition_cache: Dict[frozenset, float] = {}

        def get_val(subset: frozenset) -> float:
            if subset not in coalition_cache:
                coalition_cache[subset] = value_function(list(subset))
            return coalition_cache[subset]

        for i, feature in enumerate(features):
            other_features = [f for f in features if f != feature]
            phi_i = 0.0

            # Iterate over all subset sizes of other features
            for s_size in range(len(other_features) + 1):
                weight = (math.factorial(s_size) * math.factorial(n - s_size - 1)) / math.factorial(n)

                for subset_tuple in itertools.combinations(other_features, s_size):
                    s = frozenset(subset_tuple)
                    s_union_i = frozenset(subset_tuple + (feature,))

                    marginal_contribution = get_val(s_union_i) - get_val(s)
                    phi_i += weight * marginal_contribution

            shapley_values[feature] = round(phi_i, 4)

        return shapley_values

    @classmethod
    def evaluate_with_global_model(
        cls,
        global_model, # GlobalKPIModel instance
        anomaly_row, # pd.DataFrame single row
    ) -> Dict[str, Any]:
        """Runs the true SHAP TreeExplainer against the XGBoost global model."""
        from kpi_engine.ml.shap_explainer import LocalShapExplainer
        
        if not global_model or not global_model.is_trained():
            return {}
            
        explainer = LocalShapExplainer(global_model.model, global_model.X_background)
        attributions = explainer.explain_anomaly(anomaly_row)
        
        # We also create a mapped dictionary for our specific features
        # so the rest of the code works cleanly.
        shap_vals = {
            "competitor_promotion": attributions.get("competitor_price", 0.0),
            "weather_heatwave": attributions.get("weather_severity", 0.0),
            "server_latency": attributions.get("server_latency", 0.0),
            "marketing_spend": attributions.get("marketing_spend", 0.0),
        }
        
        return {
            "shapley_values": shap_vals,
            "relative_attribution_pct": {
                k: round(v * 100.0, 2) for k, v in shap_vals.items()
            },
            "formula": "XGBoost TreeExplainer SHAP Values",
            "raw_attributions": attributions
        }
