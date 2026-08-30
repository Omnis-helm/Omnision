# ??? Omnision: Autonomous KPI Storytelling & Causal Governance Engine

![Version](https://img.shields.io/badge/version-3.0%20(v2.0%20Extended)-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-success.svg)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-purple.svg)

**Omnision** is an enterprise-grade autonomous, closed-loop technical architecture that resolves business KPI anomalies. It drives incidents from **Shallow Detection** to **Causal Diagnosis**, **Multi-Layered Solution Synthesis**, **Multi-Agent Governance**, and **Closed-Loop Continuous Learning**.

---

## ?? The What, Why, and How

### What is Omnision?
Omnision is a self-governing analytics pipeline. Traditional dashboards (like Tableau or Datadog) simply tell you that a metric is broken. Omnision autonomously investigates *why* it broke, scopes the blast radius, enforces enterprise data security, and deploys a multi-agent LLM swarm to generate a mathematically sound, budget-constrained mitigation plan.

### Why Omnision?
Generative AI often suffers from hallucinations when given raw, unconstrained data. Omnision solves this by using a **Neuro-Symbolic Architecture**. It intentionally avoids passing raw data directly to Large Language Models. Instead, it uses rigorous, deterministic data science (Z-scores, SHAP values, Directed Acyclic Graphs) to build a tightly constrained "cage" of verified evidence. The LLM is only permitted to operate *inside* this mathematically verified cage, virtually eliminating hallucinations while respecting strict financial limits and operational realities.

### How does it work?
Omnision executes a 7-stage sequential pipeline, blending standard machine learning, vector databases (FAISS), and multi-agent orchestration (LangGraph):

```text
STAGE 0: Data Foundation (Telemetry, KPIs, Upstream/Downstream Logs, News)
   ?
STAGE 1: Detect (Rolling 30d Z-score, Cold-Start 5% Tripwire + EWMA)
   ?
STAGE 2: Scope (Causal Direction Filtering, Hybrid Security Matrix)
   ?
STAGE 3: Build Graph (The Cage: Bounded DAG Construction & Pre-Pruning)
   ?
STAGE 4: Diagnose (Composite Causal Scorer: Impact × Relevance, FAISS RAG, SHAP)
   ?
STAGE 5: Suggest (LangGraph Swarm: Prescriptive, Blue-Sky, Playbook Agents)
   ?
STAGE 6: Evaluate (The Critic: Deterministic bounds, Json Schema, Liveness Pings)
   ?
STAGE 7: Continuous Learning (RCA Overrides, e-Greedy Trust Tuning)
```

---

## ?? Enterprise Production Features (v2.0 Extended Edition)

Omnision includes subtle but critical edge-case protections required for live enterprise deployments:

1. **Alert Storm Mitigation (Super-Anchors):** If a systemic failure causes dozens of KPIs to breach simultaneously, Omnision clusters them into a single `Compound_Anchor_Node`. This prevents the system from spawning redundant, expensive LLM swarms, saving compute costs.
2. **External Web Intelligence Agent:** If internal causal evidence is weak, Omnision dynamically invokes an external agent that queries live market data via `yfinance` and runs sentiment analysis using a hosted HuggingFace **FinBERT** API to assess macroeconomic factors.
3. **Feedback Atrophy Protection ($\epsilon$-Greedy):** When an agents idea is rejected, its trust score usually decays. To prevent the system from degrading into a rigid, risk-averse echo chamber over time, Omnision shields the creative "Blue-Sky Challenger" agent from penalty decay 5% of the time.
4. **Zero-Day Incidents (Shadow Flag):** If a recommended action originates entirely from the unconstrained Blue-Sky LLM, the system tags it with `requires_shadow_run: true`, forcing RACI owners to sandbox the action before running it in production.
5. **Stale Operational Levers (Liveness Pings):** Before approving an action, the Critic performs a real-time HTTP 200 ping against the target operational endpoint (e.g., AWS, LaunchDarkly). If the endpoint is down, the action is rejected as technically infeasible.

---

## ??? Enterprise-Grade Security & Privacy

Omnision respects enterprise data boundaries before any data reaches the LLM Swarm:
* **Hybrid Security Matrix (Tier 1 & Tier 2)**: Automatically prunes highly classified entities (e.g., M&A data) or masks financial metrics (`<REDACTED_DOLLAR_VALUE>`) based on the querying users clearance level.
* **PII Redaction (Simulated Presidio)**: Automatically scans logs and support tickets, redacting Emails, Credit Cards, and SSNs.
* **Behavioral Firewall (Simulated NeMo Guardrails)**: An output scanner intercepts the LLMs recommended actions, hard-blocking destructive commands (e.g., `DROP TABLE`, `rm -rf`).

*(Note: The repository includes lightweight regex simulations of these tools to ensure the demo runs locally without heavy dependencies. For production, simply swap the modules with standard local deployments of Microsoft Presidio and NVIDIA NeMo Guardrails).*

---

## ?? Quickstart & Installation

### Prerequisites
* Python 3.9+
* Windows / Linux / macOS compatible.
* No heavy C-compiled dependencies (XGBoost/spaCy are replaced with Pure Python/Scikit-Learn equivalents for maximal OS compatibility).

### Installation
```bash
git clone https://github.com/your-org/omnision.git
cd omnision
pip install -r requirements.txt
```

### 1. Launch Interactive Web Dashboard (Streamlit)
```bash
streamlit run app.py
```
> Opens in your browser at `http://localhost:8501`.

### 2. Launch Interactive CLI Demo
```bash
# Run Scenario 1: Stripe Gateway Latency Outage
python run_demo.py --scenario SCENARIO_1_STRIPE_GATEWAY_OUTAGE

# Run Scenario 2: Multivariate Price & Volume Interaction
python run_demo.py --scenario SCENARIO_2_MULTIVARIATE_DAG_SHAP

# Run Scenario 3: Cold-Start KPI Phased Handover
python run_demo.py --scenario SCENARIO_3_COLD_START_PHASED_HANDOVER

# Run Scenario 4: Hybrid Security Matrix
python run_demo.py --scenario SCENARIO_4_SECURITY_CLEARANCE_MATRIX --role JUNIOR_ANALYST
```

### 3. Start FastAPI REST Server
```bash
uvicorn kpi_engine.api.app:app --host 0.0.0.0 --port 8000 --reload
```
> View Swagger documentation at `http://localhost:8000/docs`.

---

## ?? Business Setup Guide: Deploying to your Org

Omnision is designed to be fully domain-agnostic (Fintech, E-Commerce, Logistics). To connect it to your live business:

### Step 1: Map Your Telemetry Data
By default, Omnision uses `KartMitraDataGenerator` to synthesize data. 
1. Review `TelemetryPoint` and `CandidateNode` schemas in `kpi_engine/data/models.py`.
2. Build an ETL script (dbt/Dataform) to pull logs from your Data Warehouse (BigQuery, Snowflake) and format them into these Pydantic contracts.
3. Replace the synthetic generator in `pipeline.py` with your live database client.

### Step 2: Configure the Semantic Contracts
1. Modify the `KPISemanticContract` objects (currently mocked in `data/generator.py`).
2. Define the `domain` (e.g., `healthcare`, `ecommerce`), the `static_tripwire` limits, and the `unit` (USD, MS, Conversions).
3. Set your internal `VP_APPROVAL_REQUIRED_COST_USD` threshold in `kpi_engine/config.py`.

### Step 3: Seed the Institutional Playbook (FAISS Vector DB)
To make the "Just-in-Time Graph-RAG" truly yours:
1. Gather your companys past post-mortems, RCA documents, and standard operating procedures (SOPs).
2. Format them into text documents and inject them into the `PlaybookVectorStore` in `kpi_engine/memory/vector_store.py`.
3. Omnision will automatically embed these, injecting your exact SOPs into the AIs generation context during the next anomaly.

### Step 4: Configure the LLM
1. Open `kpi_engine/config.py`.
2. Add your `openai_api_key` or configure the `llm_provider`. 
3. *Note: If no API key is provided, the system safely falls back to a deterministic `MockLLM` for presentation and demo purposes.*

---

## ?? Mathematical Foundations

Omnision relies on rigorous mathematics before handing data to AI:

1. **Cold-Start Phased Handover (§2.2, §5.5)**:
   - Phase 1: Static Tripwire $|x - x_{\text{target}}| / x_{\text{target}} \ge 0.05$
   - Phase 2: Algorithmic Shadowing via EWMA + Surrogate Seasonality overlay
   - Phase 3: Automated Graduation to rolling 30-day $Z$-score once $N \ge 30$.

2. **Multivariate Metric DAGs (§2.5.3)**:
   $$\Delta R = P \cdot \Delta V + V \cdot \Delta P + \Delta P \cdot \Delta V$$
   Captures price effect, volume effect, and joint non-linear interaction without machine learning approximations.

3. **Master Multiplicative Composite Weight (§2.5, §5.4)**:
   $$W(A^*, n_i) = \text{Contextual Relevance} \times \text{Causal Impact}$$

4. **Telemetry-Driven Trust Weight Tuning (§4.1.2)**:
   $$W_m^{(t+1)} = W_m^{(t)} \times (1 - \eta)$$

