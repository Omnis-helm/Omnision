"""
Local SHAP Extraction Engine (On-the-Fly)
Extracts exact SHAP values for a specific anomaly timestamp using pure Python Exact Shapley (bypasses Windows DLL AppLocker blocks on numba/llvmlite).
"""
import pandas as pd
import numpy as np
import itertools
import math

class LocalShapExplainer:
    def __init__(self, model, X_background: pd.DataFrame):
        self.model = model
        self.X_background = X_background
        # Calculate the base value (expected value of the model output)
        self.base_value = float(self.model.predict(X_background).mean())

    def explain_anomaly(self, anomaly_row: pd.DataFrame) -> dict:
        """
        Calculates exact Shapley values for the specific anomaly row using the trained ML model.
        Returns a dictionary of feature -> attribution %.
        """
        # Ensure we only iterate over the features the model was trained on
        features = list(self.X_background.columns)
        n = len(features)
        
        # High-scalability fallback for >10 features
        if n > 10:
            import shap
            import logging
            logging.info(f"Feature count {n} > 10. Falling back to shap.TreeExplainer for scalability.")
            explainer = shap.TreeExplainer(self.model)
            # shap_values returns a matrix (num_samples, num_features)
            # anomaly_row is a single row DataFrame
            shap_vals = explainer.shap_values(anomaly_row)
            
            # Extract the first row of shap values
            if isinstance(shap_vals, list):
                # For some models, shap_values is a list for each class. We assume regression.
                vals = shap_vals[0][0]
            elif len(shap_vals.shape) == 2:
                vals = shap_vals[0]
            elif len(shap_vals.shape) == 3:
                vals = shap_vals[0, :, 0]
            else:
                vals = shap_vals[0]
                
            return {feat: float(val) for feat, val in zip(features, vals)}
        
        # We need a background reference for missing features.
        # We'll use the mean of the background dataset.
        bg_means = self.X_background.mean()
        
        def model_predict_subset(subset: list) -> float:
            # Create a row where features IN subset take the anomaly value,
            # and features OUT of subset take the background mean value.
            row = {}
            for f in features:
                if f in subset:
                    row[f] = anomaly_row.iloc[0][f]
                else:
                    row[f] = bg_means[f]
            
            df = pd.DataFrame([row])[features]
            return float(self.model.predict(df)[0])

        # Compute exact Shapley values (O(2^N) is fine for N=4)
        shap_values = {}
        for feature in features:
            other_features = [f for f in features if f != feature]
            phi_i = 0.0
            
            for s_size in range(len(other_features) + 1):
                weight = (math.factorial(s_size) * math.factorial(n - s_size - 1)) / math.factorial(n)
                
                for subset_tuple in itertools.combinations(other_features, s_size):
                    s_list = list(subset_tuple)
                    s_union_i = s_list + [feature]
                    
                    marginal_contribution = model_predict_subset(s_union_i) - model_predict_subset(s_list)
                    phi_i += weight * marginal_contribution
                    
            shap_values[feature] = phi_i
            
        # Convert raw SHAP values to percentage of total variance explained
        total_variance = sum(abs(v) for v in shap_values.values())
        if total_variance == 0:
            return {feat: 0.0 for feat in features}
            
        attributions = {}
        for feat, shap_val in shap_values.items():
            percentage = float(abs(shap_val) / total_variance)
            direction = 1 if shap_val > 0 else -1
            attributions[feat] = percentage * direction
            
        return attributions
