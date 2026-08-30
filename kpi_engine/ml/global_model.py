"""
Global Training Engine (Batch Process)
Simulates background training of an XGBoost model on historical telemetry.
"""
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

class GlobalKPIModel:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.X_background = None

    def train_global_model(self, df: pd.DataFrame, target_col: str = "kpi_value"):
        """Trains the global GradientBoostingRegressor on historical telemetry."""
        if target_col not in df.columns:
            raise ValueError(f"Target {target_col} not found in dataframe.")
            
        # Drop date/time cols for training
        X = df.drop(columns=[target_col, "date"], errors="ignore")
        y = df[target_col]
        
        self.feature_names = X.columns.tolist()
        self.X_background = X
        
        # Train a fast, lightweight Sklearn Regressor (avoids Windows DLL blocks on xgboost)
        self.model = GradientBoostingRegressor(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X, y)
        
        return self.model

    def is_trained(self):
        return self.model is not None
