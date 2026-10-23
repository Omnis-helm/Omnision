"""
Local SHAP Extraction Engine (on-the-fly)

Exact interventional Shapley values for one anomaly row: features outside a coalition take the
background mean. All 2^N coalitions are predicted in a single batched call, so N<=12 stays fast and
needs no numba/llvmlite (avoids Windows AppLocker issues with the `shap` package). For larger N the
`shap.TreeExplainer` is used if installed.
"""
import itertools
import math
from typing import Dict, Any

import numpy as np
import pandas as pd


class LocalShapExplainer:
    MAX_EXACT_FEATURES = 12

    def __init__(self, model, X_background: pd.DataFrame):
        self.model = model
        self.X_background = X_background
        self.features = list(X_background.columns)
        self.bg_means = X_background.mean()
        self.base_value = float(self.model.predict(pd.DataFrame([self.bg_means])[self.features])[0])

    def _exact(self, x: pd.Series) -> Dict[str, float]:
        n = len(self.features)
        coalitions = list(itertools.product([0, 1], repeat=n))
        rows = []
        for mask in coalitions:
            rows.append({f: (x[f] if m else self.bg_means[f]) for f, m in zip(self.features, mask)})
        preds = self.model.predict(pd.DataFrame(rows)[self.features])
        value = {mask: float(p) for mask, p in zip(coalitions, preds)}

        phi = {}
        for i, feat in enumerate(self.features):
            total = 0.0
            for mask in coalitions:
                if mask[i] == 1:
                    continue
                s = sum(mask)
                weight = math.factorial(s) * math.factorial(n - s - 1) / math.factorial(n)
                with_i = mask[:i] + (1,) + mask[i + 1:]
                total += weight * (value[with_i] - value[mask])
            phi[feat] = total
        return phi

    def explain_anomaly(self, anomaly_row: pd.DataFrame) -> Dict[str, Any]:
        x = anomaly_row.iloc[0]
        if len(self.features) <= self.MAX_EXACT_FEATURES:
            phi = self._exact(x)
            method = "Exact interventional Shapley (batched, 2^N coalitions)"
        else:  # pragma: no cover
            import shap
            vals = np.asarray(shap.TreeExplainer(self.model).shap_values(anomaly_row[self.features]))
            vals = vals.reshape(-1, len(self.features))[0]
            phi = {f: float(v) for f, v in zip(self.features, vals)}
            method = "shap.TreeExplainer"

        prediction = float(self.model.predict(anomaly_row[self.features])[0])
        total_abs = sum(abs(v) for v in phi.values())
        relative = {f: (v / total_abs if total_abs else 0.0) for f, v in phi.items()}
        return {
            "shap_values": {f: round(v, 2) for f, v in phi.items()},
            "relative_attribution": {f: round(v, 4) for f, v in relative.items()},
            "base_value": round(self.base_value, 2),
            "prediction": round(prediction, 2),
            "additivity_gap": round(prediction - self.base_value - sum(phi.values()), 4),
            "feature_values": {f: round(float(x[f]), 4) for f in self.features},
            "method": method,
        }
