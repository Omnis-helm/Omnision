"""
Shallow Telemetry Anomaly Detection Pipeline (§2.2, §5.2)
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
from kpi_engine.detector.cold_start import ColdStartAnomalyManager
from kpi_engine.config import CONFIG


class TelemetryAnomalyDetector:
    """Monitors continuous daily structured business metrics and raises Anchor Nodes."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.cold_start_mgr = ColdStartAnomalyManager(config)

    def evaluate_metric(
        self,
        contract: KPISemanticContract,
        history: List[TelemetryPoint],
        current_point: TelemetryPoint,
        surrogate_history: Optional[List[TelemetryPoint]] = None,
    ) -> Tuple[bool, Optional[AnchorNode]]:
        """Scan a single metric point against its contract and history."""
        # If Cold Start, route to Phased Handover manager
        if contract.lifecycle_stage == LifecycleStage.COLD_START:
            is_anomaly, anchor, _ = self.cold_start_mgr.evaluate_cold_start_kpi(
                contract, history, current_point, surrogate_history
            )
            return is_anomaly, anchor

        # Mature KPI: Standard 30-day rolling baseline
        if not history:
            return False, None

        # Extract last 30 days
        window_points = history[-self.config.mature_history_days:]
        values = [p.value for p in window_points]
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
                trigger_rule="Z_SCORE_ANOMALY",
            )
            return True, anchor

        # Dual-Window Systemic Drift Check (The Boiling Frog Solution)
        import pandas as pd
        all_values = values + [current_point.value]
        if len(all_values) >= self.config.slow_ewma_days:
            series = pd.Series(all_values)
            fast_ewma = series.ewm(span=self.config.fast_ewma_days, adjust=False).mean().iloc[-1]
            slow_ewma = series.ewm(span=self.config.slow_ewma_days, adjust=False).mean().iloc[-1]
            drift_pct = ((fast_ewma - slow_ewma) / slow_ewma) * 100.0

            if abs(drift_pct) >= self.config.systemic_drift_threshold_pct:
                anchor = AnchorNode(
                    kpi_id=contract.kpi_id,
                    metric_name=contract.name,
                    timestamp=current_point.timestamp,
                    current_value=current_point.value,
                    baseline_mean=round(slow_ewma, 4),
                    baseline_std=round(std_val, 4),
                    variance_pct=round(drift_pct, 2),
                    z_score=round(z_score, 2),
                    lifecycle_stage=LifecycleStage.MATURE,
                    dimensions=current_point.dimensions,
                    trigger_rule="SYSTEMIC_DRIFT_ANOMALY",
                )
                return True, anchor

        return False, None

    def scan_fleet(
        self,
        contracts: Dict[str, KPISemanticContract],
        telemetry_series: Dict[str, List[TelemetryPoint]],
    ) -> List[AnchorNode]:
        """Scan all telemetry series for anomalous anchor nodes."""
        anchors = []
        for kpi_id, contract in contracts.items():
            series = telemetry_series.get(kpi_id, [])
            if not series:
                continue

            current_point = series[-1]
            history = series[:-1]

            surrogate_history = None
            if contract.surrogate_reference:
                surrogate_history = telemetry_series.get(contract.surrogate_reference, [])

            is_anomaly, anchor = self.evaluate_metric(
                contract, history, current_point, surrogate_history
            )
            if is_anomaly and anchor:
                anchors.append(anchor)

        return anchors
