"""
Global Training Engine (Batch Process)
Trains an XGBoost (or GradientBoosting) regressor on historical telemetry.
"""
import pandas as pd
import threading
from sklearn.ensemble import GradientBoostingRegressor
from kpi_engine.ml.local_ml_engine import ThreadSafeModelLoader

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

_GLOBAL_MODEL_LOCK = threading.Lock()
_CACHED_GLOBAL_MODEL = None


import os
import pickle
from pathlib import Path

MODEL_FILE_PATH = Path(__file__).resolve().parent / "saved_global_model.pkl"

class GlobalKPIModel:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.X_background = None

    def save_to_disk(self, filepath=MODEL_FILE_PATH):
        """Saves the trained model state to disk."""
        try:
            with open(filepath, "wb") as f:
                pickle.dump({
                    "model": self.model,
                    "feature_names": self.feature_names,
                    "X_background": self.X_background
                }, f)
        except Exception:
            pass

    def load_from_disk(self, filepath=MODEL_FILE_PATH) -> bool:
        """Loads a pre-trained model state from disk if available."""
        if not filepath.exists():
            return False
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
                self.model = data.get("model")
                self.feature_names = data.get("feature_names", [])
                self.X_background = data.get("X_background")
                return self.model is not None
        except Exception:
            return False

    def train_global_model(self, df: pd.DataFrame, target_col: str = "kpi_value", force_retrain: bool = False):
        """Trains or loads the global XGBoost (or GradientBoosting) regressor with in-memory & disk caching."""
        global _CACHED_GLOBAL_MODEL
        if not force_retrain and _CACHED_GLOBAL_MODEL is not None:
            self.model = _CACHED_GLOBAL_MODEL.model
            self.feature_names = _CACHED_GLOBAL_MODEL.feature_names
            self.X_background = _CACHED_GLOBAL_MODEL.X_background
            return self.model

        with _GLOBAL_MODEL_LOCK:
            if not force_retrain and _CACHED_GLOBAL_MODEL is not None:
                self.model = _CACHED_GLOBAL_MODEL.model
                self.feature_names = _CACHED_GLOBAL_MODEL.feature_names
                self.X_background = _CACHED_GLOBAL_MODEL.X_background
                return self.model

            # Try loading pre-trained model from disk first
            if not force_retrain and self.load_from_disk():
                _CACHED_GLOBAL_MODEL = self
                return self.model

            if target_col not in df.columns:
                raise ValueError(f"Target {target_col} not found in dataframe.")
                
            X = df.drop(columns=[target_col, "date"], errors="ignore")
            y = df[target_col]
            
            self.feature_names = X.columns.tolist()
            self.X_background = X
            
            if XGBOOST_AVAILABLE:
                try:
                    self.model = xgb.XGBRegressor(
                        n_estimators=50,
                        max_depth=4,
                        learning_rate=0.1,
                        random_state=42
                    )
                    self.model.fit(X, y)
                except Exception:
                    self.model = GradientBoostingRegressor(
                        n_estimators=50,
                        max_depth=4,
                        learning_rate=0.1,
                        random_state=42
                    )
                    self.model.fit(X, y)
            else:
                self.model = GradientBoostingRegressor(
                    n_estimators=50,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=42
                )
                self.model.fit(X, y)
            
            self.save_to_disk()
            _CACHED_GLOBAL_MODEL = self
            return self.model

    def is_trained(self):
        return self.model is not None


