"""
Test Suite for Cold-Start Anomaly Pipeline & Phased Handover (§2.2, §5.5)
"""

import pytest
from datetime import datetime, timedelta

from kpi_engine.data.models import KPISemanticContract, LifecycleStage, TelemetryPoint
from kpi_engine.detector.cold_start import ColdStartAnomalyManager


def test_cold_start_phase1_tripwire():
    """Verify that a Day-1 KPI with < 30 samples triggers on 5% static tripwire."""
    mgr = ColdStartAnomalyManager()
    base_time = datetime(2026, 8, 30, 10, 0, 0)

    contract = KPISemanticContract(
        kpi_id="KPI_COLD_NEW_CHECKOUT_FLOW",
        name="New 1-Click Mobile Checkout Conversion",
        domain="downstream",
        lifecycle_stage=LifecycleStage.COLD_START,
        static_tripwire=0.05,
        graduation_threshold=30,
        target_value=4.00,
    )

    # 3 days of data
    history = [
        TelemetryPoint(timestamp=base_time - timedelta(days=2), kpi_id=contract.kpi_id, value=4.02),
        TelemetryPoint(timestamp=base_time - timedelta(days=1), kpi_id=contract.kpi_id, value=3.98),
    ]

    # Current point with 8.75% drop
    current_point = TelemetryPoint(
        timestamp=base_time,
        kpi_id=contract.kpi_id,
        value=3.65,
        dimensions={"platform": "iOS"},
    )

    is_anomaly, anchor, updated_contract = mgr.evaluate_cold_start_kpi(
        contract, history, current_point
    )

    assert is_anomaly is True
    assert anchor is not None
    assert anchor.trigger_rule == "COLD_START_TRIPWIRE"
    assert anchor.lifecycle_stage == LifecycleStage.COLD_START
    assert anchor.current_value == 3.65


def test_cold_start_phase3_graduation():
    """Verify that once N >= 30 samples, the KPI graduates to MATURE and standard Z-score applies."""
    mgr = ColdStartAnomalyManager()
    base_time = datetime(2026, 8, 30, 10, 0, 0)

    contract = KPISemanticContract(
        kpi_id="KPI_COLD_GRADUATING",
        name="Graduating Metric",
        domain="downstream",
        lifecycle_stage=LifecycleStage.COLD_START,
        static_tripwire=0.05,
        graduation_threshold=30,
        target_value=5.00,
    )

    # Generate 32 mature history points
    history = [
        TelemetryPoint(
            timestamp=base_time - timedelta(days=35 - i),
            kpi_id=contract.kpi_id,
            value=5.00 + (0.05 if i % 2 == 0 else -0.05),
        )
        for i in range(32)
    ]

    # Anomaly drop to 4.20 (Z-score > 5)
    current_point = TelemetryPoint(
        timestamp=base_time,
        kpi_id=contract.kpi_id,
        value=4.20,
    )

    is_anomaly, anchor, updated_contract = mgr.evaluate_cold_start_kpi(
        contract, history, current_point
    )

    assert is_anomaly is True
    assert anchor is not None
    assert updated_contract.lifecycle_stage == LifecycleStage.MATURE
    assert anchor.trigger_rule == "Z_SCORE_GRADUATED_ANOMALY"
    assert anchor.z_score > 3.0
