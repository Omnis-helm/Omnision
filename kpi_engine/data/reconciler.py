import pandas as pd

class HeterogeneousDataReconciler:
    """
    Reconciles multi-grain, multi-source telemetry into a unified daily KPI dataframe.
    Simulates enterprise data ingestion (ETL) across streaming and batch sources.
    """
    def reconcile(self, web_df: pd.DataFrame, it_df: pd.DataFrame, sales_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
        # 1. Aggregate high-frequency Web Analytics (Hourly -> Daily)
        web_df_daily = web_df.set_index("timestamp").resample('D').mean().reset_index()
        
        # 2. Aggregate high-frequency IT Telemetry (Minutely -> Daily)
        it_df_daily = it_df.set_index("timestamp").resample('D').mean().reset_index()
        
        # 3. Process low-frequency Market Data (Weekly -> forward-fill to Daily)
        # Create a full date range
        min_date = market_df["timestamp"].min().normalize()
        max_date = sales_df["timestamp"].max().normalize()
        daily_index = pd.date_range(start=min_date, end=max_date, freq='D')
        
        market_df_daily = market_df.set_index("timestamp").reindex(daily_index).ffill().reset_index()
        market_df_daily = market_df_daily.rename(columns={"index": "timestamp"})
        
        # 4. Join all sources onto the Daily Sales dataframe
        final_df = sales_df.copy()
        
        # Convert all timestamps to normalized dates for joining
        final_df["date"] = final_df["timestamp"].dt.normalize()
        web_df_daily["date"] = web_df_daily["timestamp"].dt.normalize()
        it_df_daily["date"] = it_df_daily["timestamp"].dt.normalize()
        market_df_daily["date"] = market_df_daily["timestamp"].dt.normalize()
        
        final_df = final_df.merge(web_df_daily.drop(columns=["timestamp"]), on="date", how="left")
        final_df = final_df.merge(it_df_daily.drop(columns=["timestamp"]), on="date", how="left")
        final_df = final_df.merge(market_df_daily.drop(columns=["timestamp"]), on="date", how="left")
        
        # Clean up timestamp columns
        final_df = final_df.drop(columns=["timestamp"])
        
        return final_df
