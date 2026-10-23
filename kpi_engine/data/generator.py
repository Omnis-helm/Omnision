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

    # Ambient drivers of West daily net revenue used by the global ML model (Stage 4 SHAP)
    REVENUE_BASE_USD = 350000.0
    REVENUE_COEFFS = {
        "marketing_spend": 5.0,        # +$5 revenue per $1 of spend above $10k
        "competitor_price": 3000.0,    # competitor cutting price by $1 costs us $3k/day
        "weather_severity": -6000.0,   # per unit of heat/grid severity index above 2.0
        "server_latency": -600.0,      # per ms of p50 latency above 45ms
    }
    FEATURE_BASELINES = {"marketing_spend": 10000.0, "competitor_price": 50.0, "weather_severity": 2.0, "server_latency": 45.0}

    def generate_raw_sources(
        self, days: int = 365
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, datetime]:
        """Generates 4 heterogeneous sources whose reconciled daily table drives West daily net revenue.

        Sources (cadence): Web analytics (hourly), IT telemetry (15-min), Sales SQL (daily),
        Market vendor feed (weekly snapshots + an ad-hoc snapshot on the anomaly day).
        The final day reproduces Scenario 2: RivalRetail's 20% flash sale (competitor price 50 -> 40),
        a heatwave (weather index 4.5) and slightly elevated latency, producing a ~$48k revenue drop.
        """
        rng = np.random.default_rng(42)
        end_day = self.base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        dates = [end_day - timedelta(days=days - 1 - i) for i in range(days)]

        marketing_spend = rng.normal(10000, 1500, days)
        server_latency = rng.normal(45, 8, days)
        n_weeks = days // 7 + 1
        competitor_weekly = rng.normal(50, 4, n_weeks)
        weather_weekly = np.clip(rng.normal(2.0, 0.8, n_weeks), 0.0, None)
        competitor_price = np.array([competitor_weekly[i // 7] for i in range(days)])
        weather_severity = np.array([weather_weekly[i // 7] for i in range(days)])

        # Anomaly day (Scenario 2)
        competitor_price[-1] = 40.0
        weather_severity[-1] = 4.5
        server_latency[-1] = 50.0
        marketing_spend[-1] = 10000.0

        def revenue_fn(mkt, comp, wea, lat):
            b = self.FEATURE_BASELINES
            c = self.REVENUE_COEFFS
            return (self.REVENUE_BASE_USD
                    + c["marketing_spend"] * (mkt - b["marketing_spend"])
                    + c["competitor_price"] * (comp - b["competitor_price"])
                    + c["weather_severity"] * (wea - b["weather_severity"])
                    + c["server_latency"] * (lat - b["server_latency"]))

        regional_revenue = revenue_fn(marketing_spend, competitor_price, weather_severity, server_latency)
        regional_revenue = regional_revenue + rng.normal(0, 4000, days)
        regional_revenue[-1] = revenue_fn(marketing_spend[-1], competitor_price[-1], weather_severity[-1], server_latency[-1])

        aov = rng.normal(100, 3, days)
        orders = regional_revenue / aov
        traffic = orders / 0.032  # ~3.2% conversion
        cart_abandonment = rng.normal(68, 2, days)

        # Source 1: Web analytics (hourly)
        web_rows = []
        for i, d in enumerate(dates):
            for h in range(24):
                web_rows.append((d + timedelta(hours=h), traffic[i] / 24 + rng.normal(0, 20), cart_abandonment[i] + rng.normal(0, 1)))
        web_df = pd.DataFrame(web_rows, columns=["timestamp", "traffic", "cart_abandonment"])
        # Hourly traffic is a count -> daily SUM; restore to per-day units in the reconciler via mean*24
        web_df["traffic"] = web_df["traffic"] * 24

        # Source 2: IT telemetry (every 15 minutes)
        it_rows = []
        for i, d in enumerate(dates):
            for m in range(0, 24 * 60, 15):
                it_rows.append((d + timedelta(minutes=m), server_latency[i] + rng.normal(0, 2)))
        it_df = pd.DataFrame(it_rows, columns=["timestamp", "server_latency"])
        # Remove the zero-mean measurement noise from the daily aggregate exactly
        it_df["server_latency"] = it_df.groupby(it_df["timestamp"].dt.normalize())["server_latency"].transform(
            lambda x: x - x.mean()) + np.repeat(server_latency, 96)

        # Source 3: Market vendor feed (weekly snapshots + anomaly-day snapshot)
        snap_idx = list(range(0, days, 7))
        if days - 1 not in snap_idx:
            snap_idx.append(days - 1)
        market_df = pd.DataFrame({
            "timestamp": [dates[i] for i in snap_idx],
            "competitor_price": [competitor_price[i] for i in snap_idx],
            "weather_severity": [weather_severity[i] for i in snap_idx],
        })

        # Source 4: Sales SQL (daily)
        sales_df = pd.DataFrame({
            "timestamp": dates,
            "regional_revenue": regional_revenue,
            "aov": aov,
            "marketing_spend": marketing_spend,
        })

        return web_df, it_df, sales_df, market_df, end_day
