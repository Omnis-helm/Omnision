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

    def generate_raw_sources(self, days: int = 35) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, datetime]:
        """Generates 4 distinct heterogeneous data sources with 5 mathematically connected KPIs."""
        base_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days-1)
        dates = [base_time + timedelta(days=i) for i in range(days)]
        
        np.random.seed(42)
        marketing_spend = np.random.normal(10000, 1500, days)
        competitor_price = np.random.normal(50, 5, days)
        weather_severity = np.random.normal(2, 0.5, days)
        server_latency = np.random.normal(45, 10, days)
        
        kpi_value = 100 + (marketing_spend/1000 * 0.3) - (competitor_price * 0.5) - (weather_severity * 0.2) - (server_latency * 0.1) + np.random.normal(0, 1, days)
        
        # Anomaly
        competitor_price[-1] = 30.0
        weather_severity[-1] = 4.5
        server_latency[-1] = 50.0
        kpi_value[-1] = 100 + (marketing_spend[-1]/1000 * 0.3) - (competitor_price[-1] * 0.5) - (weather_severity[-1] * 0.2) - (server_latency[-1] * 0.1)

        # 5 Connected KPIs
        traffic = np.random.normal(25000, 2000, days)
        aov = np.random.normal(65, 3, days)
        cart_abandonment = 100 - (kpi_value * 0.5) + np.random.normal(0, 2, days)
        regional_revenue = traffic * (kpi_value / 100) * aov
        
        # Source 1: Web Analytics (Hourly)
        web_timestamps = []
        web_traffic = []
        web_abandonment = []
        for i, d in enumerate(dates):
            for h in range(24):
                web_timestamps.append(d + timedelta(hours=h))
                web_traffic.append(traffic[i] + np.random.normal(0, 100))
                web_abandonment.append(cart_abandonment[i] + np.random.normal(0, 1))
        web_df = pd.DataFrame({"timestamp": web_timestamps, "traffic": web_traffic, "cart_abandonment": web_abandonment})
        
        # Source 2: IT Logs (Minutely) - simulated as every 15 mins for performance
        it_timestamps = []
        it_latency = []
        for i, d in enumerate(dates):
            for m in range(0, 24*60, 15):
                it_timestamps.append(d + timedelta(minutes=m))
                it_latency.append(server_latency[i] + np.random.normal(0, 2))
        it_df = pd.DataFrame({"timestamp": it_timestamps, "server_latency": it_latency})
        
        # Source 3: Market Data (Weekly Snapshot)
        market_timestamps = []
        market_comp = []
        market_weather = []
        for i in range(0, days, 7):
            market_timestamps.append(dates[i])
            market_comp.append(competitor_price[i])
            market_weather.append(weather_severity[i])
        if dates[-1] not in market_timestamps:
            market_timestamps.append(dates[-1])
            market_comp.append(competitor_price[-1])
            market_weather.append(weather_severity[-1])
            
        market_df = pd.DataFrame({
            "timestamp": market_timestamps, 
            "competitor_price": market_comp, 
            "weather_severity": market_weather
        })
        
        # Source 4: Sales SQL (Daily)
        sales_df = pd.DataFrame({
            "timestamp": dates,
            "kpi_value": kpi_value,
            "regional_revenue": regional_revenue,
            "aov": aov,
            "marketing_spend": marketing_spend
        })
        
        return web_df, it_df, sales_df, market_df, base_time
