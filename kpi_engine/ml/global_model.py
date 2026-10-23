"""
Global Training Engine (batch process)

Trains an XGBoost regressor (GradientBoostingRegressor fallback) that predicts West daily net revenue
from *ambient drivers only* (marketing spend, competitor price, weather severity, server latency).
Outcome columns that are arithmetically derived from revenue (traffic, AOV, orders, cart abandonment)
are deliberately excluded to avoid target leakage.

The fitted model is cached in memory and on disk. The pickle stores a schema signature; a model saved
with different features / version is ignored and retrained.
"""
import hashlib
import json
import logging
import pickle
import threading
from pathlib import Path
from typing import List, Optional

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    XGBOOST_AVAILABLE = False

logger = logging.getLogger(__name__)

MODEL_SCHEMA_VERSION = 2
DEFAULT_FEATURES: List[str] = ["marketing_spend", "competitor_price", "weather_severity", "server_latency"]
DEFAULT_TARGET = "regional_revenue"
MODEL_FILE_PATH = Path(__file__).resolve().parent / "saved_global_model.pkl"

_GLOBAL_MODEL_LOCK = threading.Lock()
_CACHED_STATE: Optional[dict] = None


def _signature(features: List[str], target: str, n_rows: int) -> str:
    raw = json.dumps({"v": MODEL_SCHEMA_VERSION, "features": features, "target": target,
                      "xgb": XGBOOST_AVAILABLE, "rows": n_rows}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class GlobalKPIModel:
    def __init__(self, features: Optional[List[str]] = None, target_col: str = DEFAULT_TARGET):
        self.features = list(features or DEFAULT_FEATURES)
        self.target_col = target_col
        self.model = None
        self.feature_names: List[str] = []
        self.X_background: Optional[pd.DataFrame] = None
        self.model_type = "untrained"
        self.train_r2: Optional[float] = None
        self.signature: Optional[str] = None

    # ------------------------------------------------------------------ persistence
    def _state(self) -> dict:
        return {"model": self.model, "feature_names": self.feature_names, "X_background": self.X_background,
                "model_type": self.model_type, "train_r2": self.train_r2, "signature": self.signature}

    def _load_state(self, st: dict):
        self.model = st["model"]
        self.feature_names = st["feature_names"]
        self.X_background = st["X_background"]
        self.model_type = st.get("model_type", "unknown")
        self.train_r2 = st.get("train_r2")
        self.signature = st.get("signature")

    def save_to_disk(self, filepath: Path = MODEL_FILE_PATH):
        try:
            with open(filepath, "wb") as f:
                pickle.dump(self._state(), f)
        except Exception as e:
            logger.warning("Failed to save model to disk: %s", e)

    def load_from_disk(self, expected_signature: str, filepath: Path = MODEL_FILE_PATH) -> bool:
        """Loads a model only if it was produced by this code with the same schema (local, trusted file)."""
        if not filepath.exists():
            return False
        try:
            with open(filepath, "rb") as f:
                st = pickle.load(f)
            if not isinstance(st, dict) or st.get("signature") != expected_signature:
                return False
            self._load_state(st)
            return self.model is not None
        except Exception as e:
            logger.warning("Failed to load model from disk: %s", e)
            return False

    # ------------------------------------------------------------------ training
    def _new_estimator(self):
        if XGBOOST_AVAILABLE:
            return xgb.XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
                                    random_state=42), "XGBRegressor"
        return GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
                                         random_state=42), "GradientBoostingRegressor"

    def train_global_model(self, df: pd.DataFrame, target_col: Optional[str] = None, force_retrain: bool = False,
                           exclude_last_n: int = 1):
        """Fit on all rows except the last `exclude_last_n` (the anomaly day must not be in training)."""
        global _CACHED_STATE
        target_col = target_col or self.target_col
        if target_col not in df.columns:
            raise ValueError(f"Target {target_col} not found in dataframe.")
        missing = [f for f in self.features if f not in df.columns]
        if missing:
            raise ValueError(f"Features missing from dataframe: {missing}")

        train_df = df.iloc[:-exclude_last_n] if exclude_last_n else df
        sig = _signature(self.features, target_col, len(train_df))

        with _GLOBAL_MODEL_LOCK:
            if not force_retrain and _CACHED_STATE is not None and _CACHED_STATE.get("signature") == sig:
                self._load_state(_CACHED_STATE)
                return self.model
            if not force_retrain and self.load_from_disk(sig):
                _CACHED_STATE = self._state()
                return self.model

            X = train_df[self.features].astype(float)
            y = train_df[target_col].astype(float)
            est, name = self._new_estimator()
            try:
                est.fit(X, y)
            except Exception as e:
                logger.warning("%s failed (%s); falling back to GradientBoostingRegressor", name, e)
                est = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42)
                name = "GradientBoostingRegressor"
                est.fit(X, y)

            self.model = est
            self.model_type = name
            self.feature_names = list(self.features)
            self.X_background = X
            self.train_r2 = round(float(est.score(X, y)), 4)
            self.signature = sig
            self.save_to_disk()
            _CACHED_STATE = self._state()
            return self.model

    def is_trained(self) -> bool:
        return self.model is not None
