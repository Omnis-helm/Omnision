"""
Cold-Start Anomaly Pipeline & Phased Handover State Machine (§2.2, §5.5)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime

from kpi_engine.data.models import (
    KPISemanticContract,
    LifecycleStage,
    TelemetryPoint,
    AnchorNode,
)
from kpi_engine.config import CONFIG


class ColdStartAnomalyManager:
    """Manages the lifecycle transition from Day-1 rule-based tripwire to statistical Z-score baseline."""

    def __init__(self, config=CONFIG):
        self.config = config

    def compute_ewma_baseline(
        self,
        values: List[float],
        alpha: Optional[float] = None,
    ) -> float:
        """Compute Exponentially Weighted Moving Average baseline."""
        if not values:
            return 0.0
        alpha = alpha or self.config.cold_start_ewma_alpha
        ewma = values[0]
        for v in values[1:]:
            ewma = alpha * v + (1.0 - alpha) * ewma
        return round(float(ewma), 4)

    def apply_surrogate_seasonality(
        self,
        current_value: float,
        target_value: float,
        surrogate_points: List[TelemetryPoint],
    ) -> float:
        """Overlay historical variance curve of a mature sibling KPI onto the cold-start KPI."""
        if not surrogate_points or len(surrogate_points) < 7:
            return target_value

        surrogate_values = [p.value for p in surrogate_points]
        surr_mean = float(np.mean(surrogate_values))
        surr_latest = surrogate_points[-1].value

        if surr_mean == 0:
            return target_value

        seasonality_factor = surr_latest / surr_mean
        simulated_baseline = target_value * seasonality_factor
        return round(simulated_baseline, 4)

    def evaluate_cold_start_kpi(
        self,
        contract: KPISemanticContract,
        history: List[TelemetryPoint],
        current_point: TelemetryPoint,
        surrogate_history: Optional[List[TelemetryPoint]] = None,
    ) -> Tuple[bool, Optional[AnchorNode], KPISemanticContract]:
        """Evaluate cold-start KPI against Phased Handover mechanism.
        Returns: (is_anomaly, anchor_node_or_none, updated_contract)
        """
        n_samples = len(history)

        # Phase 3 Check: Automated Graduation to MATURE if N >= graduation_threshold
        if n_samples >= contract.graduation_threshold:
            contract.lifecycle_stage = LifecycleStage.MATURE
            # Evaluated under mature statistical pipeline
            values = [p.value for p in history]
            mean_val = float(np.mean(values))
            std_val = float(np.std(values)) or 0.001
            z_score = abs(current_point.value - mean_val) / std_val
            variance_pct = ((current_point.value - mean_val) / mean_val) * 100.0

            if z_score >= self.config.z_score_alert_threshold:
                anchor = AnchorNode(
                    kpi_id=contract.kpi_id,
                    metric_name=contract.name,
                    timestamp=current_point.timestamp,
                    current_value=current_point.value,
                    baseline_mean=round(mean_val, 4),
                    baseline_std=round(std_val, 4),
                    variance_pct=round(variance_pct, 2),
                    z_score=round(z_score, 2),
                    lifecycle_stage=LifecycleStage.MATURE,
                    dimensions=current_point.dimensions,
                    trigger_rule="Z_SCORE_GRADUATED_ANOMALY",
                )
                return True, anchor, contract
            return False, None, contract

        # Phase 1 & 2: Cold-Start active
        # Compute baseline via EWMA + Surrogate Seasonality
        if history:
            ewma_base = self.compute_ewma_baseline([p.value for p in history])
        else:
            ewma_base = contract.target_value

        if surrogate_history:
            effective_baseline = self.apply_surrogate_seasonality(
                current_point.value, ewma_base, surrogate_history
            )
        else:
            effective_baseline = ewma_base

        rel_deviation = abs(current_point.value - effective_baseline) / max(0.001, effective_baseline)
        variance_pct = ((current_point.value - effective_baseline) / max(0.001, effective_baseline)) * 100.0

        # Check against Phase 1 Rule-Based Tripwire (e.g., 5% deviation)
        if rel_deviation >= contract.static_tripwire:
            # Pseudo z-score based on surrogate or estimated std
            surrogate_std = float(np.std([p.value for p in surrogate_history])) if surrogate_history else (effective_baseline * 0.05)
            z_score = abs(current_point.value - effective_baseline) / max(0.001, surrogate_std)

            anchor = AnchorNode(
                kpi_id=contract.kpi_id,
                metric_name=contract.name,
                timestamp=current_point.timestamp,
                current_value=current_point.value,
                baseline_mean=round(effective_baseline, 4),
                baseline_std=round(surrogate_std, 4),
                variance_pct=round(variance_pct, 2),
                z_score=round(z_score, 2),
                lifecycle_stage=LifecycleStage.COLD_START,
                dimensions=current_point.dimensions,
                trigger_rule="COLD_START_TRIPWIRE",
            )
            return True, anchor, contract

        return False, None, contract
