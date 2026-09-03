file_path = r"D:\projects\Omnision\Omnision\kpi_engine\data\generator.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """    def generate_multivariate_dataframe(self, days: int = 35) -> pd.DataFrame:
        \"\"\"Generates historical tabular data to train the XGBoost Global Model.\"\"\"
        base_time = datetime.now(timezone.utc) - timedelta(days=days)
        dates = [base_time + timedelta(days=i) for i in range(days)]
        
        # Synthetic baseline features
        np.random.seed(42)
        marketing_spend = np.random.normal(10000, 1500, days)
        competitor_price = np.random.normal(50, 5, days)
        weather_severity = np.random.normal(2, 0.5, days)
        server_latency = np.random.normal(45, 10, days)
        
        # NOTE: small N by design ?" ground-truth formula below, not meant to generalize
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
        
        return df, base_time"""
        
replacement = """    def generate_raw_sources(self, days: int = 35) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, datetime]:
        \"\"\"Generates 4 distinct heterogeneous data sources with 5 mathematically connected KPIs.\"\"\"
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
        
        return web_df, it_df, sales_df, market_df, base_time"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Replaced target in generator.py")
else:
    print("Target not found in generator.py")
