"""
KartMitra Enterprise Synthetic Data Generator (30-45 days telemetry + Unstructured Logs)
"""

import math
import random
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from kpi_engine.data.models import (
    KPISemanticContract,
    LifecycleStage,
    SecurityTier,
    UserClearance,
    TelemetryPoint,
    CandidateNode,
    CandidateNodeType,
)


class KartMitraDataGenerator:
    """Generates realistic enterprise business telemetry and value-chain evidence."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        self.base_time = datetime(2026, 8, 30, 10, 0, 0)

    def generate_contracts(self) -> Dict[str, KPISemanticContract]:
        """Define semantic contracts for enterprise KPIs."""
        contracts = {
            "KPI_WEST_CHECKOUT_CONV": KPISemanticContract(
                kpi_id="KPI_WEST_CHECKOUT_CONV",
                name="West Region Checkout Conversion Rate",
                domain="downstream",
                lifecycle_stage=LifecycleStage.MATURE,
                static_tripwire=0.05,
                graduation_threshold=30,
                unit="%",
                target_value=3.20,
            ),
            "KPI_EAST_CHECKOUT_CONV": KPISemanticContract(
                kpi_id="KPI_EAST_CHECKOUT_CONV",
                name="East Region Checkout Conversion Rate (Mature Benchmark)",
                domain="downstream",
                lifecycle_stage=LifecycleStage.MATURE,
                static_tripwire=0.05,
                graduation_threshold=30,
                unit="%",
                target_value=3.40,
            ),
            "KPI_REVENUE_WEST": KPISemanticContract(
                kpi_id="KPI_REVENUE_WEST",
                name="West Region Daily Net Revenue",
                domain="financials",
                lifecycle_stage=LifecycleStage.MATURE,
                static_tripwire=0.08,
                graduation_threshold=30,
                unit="USD",
                target_value=350000.0,
            ),
            "KPI_GROSS_MARGIN_WEST": KPISemanticContract(
                kpi_id="KPI_GROSS_MARGIN_WEST",
                name="West Region Gross Margin",
                domain="financials",
                lifecycle_stage=LifecycleStage.MATURE,
                static_tripwire=0.04,
                graduation_threshold=30,
                unit="%",
                target_value=42.5,
            ),
            "KPI_COGS_ELECTRONICS": KPISemanticContract(
                kpi_id="KPI_COGS_ELECTRONICS",
                name="Electronics Procurement COGS",
                domain="upstream",
                lifecycle_stage=LifecycleStage.MATURE,
                static_tripwire=0.06,
                graduation_threshold=30,
                unit="USD",
                target_value=180000.0,
            ),
            "KPI_COLD_NEW_CHECKOUT_FLOW": KPISemanticContract(
                kpi_id="KPI_COLD_NEW_CHECKOUT_FLOW",
                name="New 1-Click Mobile Checkout Conversion (Cold-Start)",
                domain="downstream",
                lifecycle_stage=LifecycleStage.COLD_START,
                static_tripwire=0.05,
                surrogate_reference="KPI_EAST_CHECKOUT_CONV",
                graduation_threshold=30,
                unit="%",
                target_value=4.10,
            ),
        }
        return contracts

    def generate_telemetry_series(
        self, days: int = 35
    ) -> Tuple[Dict[str, List[TelemetryPoint]], datetime]:
        """Generate 35 days of daily baseline telemetry points for all KPIs."""
        series: Dict[str, List[TelemetryPoint]] = {
            "KPI_WEST_CHECKOUT_CONV": [],
            "KPI_EAST_CHECKOUT_CONV": [],
            "KPI_REVENUE_WEST": [],
            "KPI_GROSS_MARGIN_WEST": [],
            "KPI_COGS_ELECTRONICS": [],
            "KPI_COLD_NEW_CHECKOUT_FLOW": [],
        }

        start_date = self.base_time - timedelta(days=days)

        for i in range(days):
            current_date = start_date + timedelta(days=i)
            dow = current_date.weekday()
            seasonality = 1.0 + 0.05 * math.sin(dow * (2 * math.pi / 7))

            # Mature West Checkout: mean 3.20%, std ~0.10%
            noise_west = np.random.normal(0, 0.08)
            val_west = max(1.0, 3.20 * seasonality + noise_west)
            series["KPI_WEST_CHECKOUT_CONV"].append(
                TelemetryPoint(
                    timestamp=current_date,
                    kpi_id="KPI_WEST_CHECKOUT_CONV",
                    value=round(val_west, 3),
                    dimensions={"region": "West", "platform": "iOS"},
                )
            )

            # Mature East Benchmark: mean 3.40%, std ~0.08%
            noise_east = np.random.normal(0, 0.07)
            val_east = max(1.0, 3.40 * seasonality + noise_east)
            series["KPI_EAST_CHECKOUT_CONV"].append(
                TelemetryPoint(
                    timestamp=current_date,
                    kpi_id="KPI_EAST_CHECKOUT_CONV",
                    value=round(val_east, 3),
                    dimensions={"region": "East", "platform": "iOS"},
                )
            )

            # Revenue: $350k baseline
            noise_rev = np.random.normal(0, 12000.0)
            val_rev = max(50000.0, 350000.0 * seasonality + noise_rev)
            series["KPI_REVENUE_WEST"].append(
                TelemetryPoint(
                    timestamp=current_date,
                    kpi_id="KPI_REVENUE_WEST",
                    value=round(val_rev, 2),
                    dimensions={"region": "West"},
                )
            )

            # Gross Margin: 42.5% baseline
            noise_margin = np.random.normal(0, 0.6)
            val_margin = 42.5 + noise_margin
            series["KPI_GROSS_MARGIN_WEST"].append(
                TelemetryPoint(
                    timestamp=current_date,
                    kpi_id="KPI_GROSS_MARGIN_WEST",
                    value=round(val_margin, 2),
                    dimensions={"region": "West"},
                )
            )

            # COGS Electronics: $180k baseline
            noise_cogs = np.random.normal(0, 5000.0)
            val_cogs = 180000.0 + noise_cogs
            series["KPI_COGS_ELECTRONICS"].append(
                TelemetryPoint(
                    timestamp=current_date,
                    kpi_id="KPI_COGS_ELECTRONICS",
                    value=round(val_cogs, 2),
                    dimensions={"category": "Electronics"},
                )
            )

            # Cold-Start KPI: Only has data for the last 6 days
            if i >= (days - 6):
                val_cold = 4.10 * seasonality + np.random.normal(0, 0.09)
                series["KPI_COLD_NEW_CHECKOUT_FLOW"].append(
                    TelemetryPoint(
                        timestamp=current_date,
                        kpi_id="KPI_COLD_NEW_CHECKOUT_FLOW",
                        value=round(val_cold, 3),
                        dimensions={"platform": "Mobile"},
                    )
                )

        return series, self.base_time

    def generate_multivariate_dataframe(self, days: int = 35) -> pd.DataFrame:
        """Generates historical tabular data to train the XGBoost Global Model."""
        base_time = datetime.now(timezone.utc) - timedelta(days=days)
        dates = [base_time + timedelta(days=i) for i in range(days)]
        
        # Synthetic baseline features
        np.random.seed(42)
        marketing_spend = np.random.normal(10000, 1500, days)
        competitor_price = np.random.normal(50, 5, days)
        weather_severity = np.random.normal(2, 0.5, days)
        server_latency = np.random.normal(45, 10, days)
        
        # Target formula: baseline + 0.3*marketing - 0.5*competitor - 0.2*weather - 0.1*latency + noise
        kpi_value = 100 + (marketing_spend/1000 * 0.3) - (competitor_price * 0.5) - (weather_severity * 0.2) - (server_latency * 0.1) + np.random.normal(0, 1, days)
        
        # Introduce the anomaly on the last day (t-0)
        # We simulate a drop caused largely by competitor price drop (they lowered prices) and a bit by weather
        competitor_price[-1] = 30.0 # Sharp drop in competitor price
        weather_severity[-1] = 4.5  # Bad weather
        server_latency[-1] = 50.0   # Normal latency
        
        # Recalculate last day KPI with the new anomaly values
        kpi_value[-1] = 100 + (marketing_spend[-1]/1000 * 0.3) - (competitor_price[-1] * 0.5) - (weather_severity[-1] * 0.2) - (server_latency[-1] * 0.1)
        
        df = pd.DataFrame({
            "date": dates,
            "marketing_spend": marketing_spend,
            "competitor_price": competitor_price,
            "weather_severity": weather_severity,
            "server_latency": server_latency,
            "kpi_value": kpi_value
        })
        
        return df, base_time
