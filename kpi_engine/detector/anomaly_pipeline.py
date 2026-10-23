"""
Shallow Telemetry Anomaly Detection Pipeline (§2.2, §5.2)

Stage 1 of the engine. Turns a KPI time series into an AnchorNode (A*) when:
  * MATURE KPIs (>= mature_history_days of history): |Z| >= z_score_alert_threshold
    on the trailing window, or a dual-window EWMA systemic drift ("boiling frog").
  * COLD_START KPIs: routed to the ColdStartAnomalyManager (static tripwire + EWMA + surrogate).
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

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
        extra_dimensions: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Optional[AnchorNode]]:
        """Scan a single metric point against its contract and history."""
        dims = {**(current_point.dimensions or {}), **(extra_dimensions or {})}
        dims.setdefault("domain", contract.domain)
        point = current_point.model_copy(update={"dimensions": dims})

        # Cold Start KPIs (or not enough history yet) -> Phased Handover manager.
        # Work on a copy so graduation does not mutate the shared contract registry.
        if contract.lifecycle_stage == LifecycleStage.COLD_START:
            is_anomaly, anchor, _ = self.cold_start_mgr.evaluate_cold_start_kpi(
                contract.model_copy(deep=True), history, point, surrogate_history
            )
            return is_anomaly, anchor

        if not history:
            return False, None

        window_points = history[-self.config.mature_history_days:]
        values = [p.value for p in window_points]
        mean_val = float(np.mean(values))
        std_val = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        std_val = std_val or 1e-3

        z_score = abs(point.value - mean_val) / std_val
        variance_pct = ((point.value - mean_val) / mean_val) * 100.0 if mean_val else 0.0

        if z_score >= self.config.z_score_alert_threshold:
            return True, AnchorNode(
                kpi_id=contract.kpi_id,
                metric_name=contract.name,
                timestamp=point.timestamp,
                current_value=point.value,
                baseline_mean=round(mean_val, 4),
                baseline_std=round(std_val, 4),
                variance_pct=round(variance_pct, 2),
                z_score=round(z_score, 2),
                lifecycle_stage=LifecycleStage.MATURE,
                dimensions=dims,
                trigger_rule="Z_SCORE_ANOMALY",
            )

        # Dual-Window Systemic Drift Check (The Boiling Frog Solution)
        all_values = values + [point.value]
        if len(all_values) >= self.config.slow_ewma_days:
            series = pd.Series(all_values)
            fast_ewma = float(series.ewm(span=self.config.fast_ewma_days, adjust=False).mean().iloc[-1])
            slow_ewma = float(series.ewm(span=self.config.slow_ewma_days, adjust=False).mean().iloc[-1])
            drift_pct = ((fast_ewma - slow_ewma) / slow_ewma) * 100.0 if slow_ewma else 0.0

            if abs(drift_pct) >= self.config.systemic_drift_threshold_pct:
                return True, AnchorNode(
                    kpi_id=contract.kpi_id,
                    metric_name=contract.name,
                    timestamp=point.timestamp,
                    current_value=point.value,
                    baseline_mean=round(slow_ewma, 4),
                    baseline_std=round(std_val, 4),
                    variance_pct=round(drift_pct, 2),
                    z_score=round(z_score, 2),
                    lifecycle_stage=LifecycleStage.MATURE,
                    dimensions=dims,
                    trigger_rule="SYSTEMIC_DRIFT_ANOMALY",
                )

        return False, None

    def scan_fleet(
        self,
        contracts: Dict[str, KPISemanticContract],
        telemetry_series: Dict[str, List[TelemetryPoint]],
    ) -> List[AnchorNode]:
        """Scan the latest point of every telemetry series for anomalous anchor nodes."""
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

            is_anomaly, anchor = self.evaluate_metric(contract, history, current_point, surrogate_history)
            if is_anomaly and anchor:
                anchors.append(anchor)

        return anchors
