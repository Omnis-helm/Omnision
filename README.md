# ðŸ‘ï¸ Omnision: Autonomous KPI Storytelling & Causal Governance Engine

![Version](https://img.shields.io/badge/version-3.0%20(v2.0%20Extended)-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-success.svg)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-purple.svg)

**Omnision** is an enterprise-grade autonomous, closed-loop technical architecture that resolves business KPI anomalies. It drives incidents from **Shallow Detection** to **Causal Diagnosis**, **Multi-Layered Solution Synthesis**, **Multi-Agent Governance**, and **Closed-Loop Continuous Learning**.

---

## ðŸ’¡ The What, Why, and How

### What is Omnision?
Omnision is a self-governing analytics pipeline. Traditional dashboards (like Tableau or Datadog) simply tell you that a metric is broken. Omnision autonomously investigates *why* it broke, scopes the blast radius, enforces enterprise data security, and deploys a multi-agent LLM swarm to generate a mathematically sound, budget-constrained mitigation plan.

### Why Omnision?
Generative AI often suffers from hallucinations when given raw, unconstrained data. Omnision solves this by using a **Neuro-Symbolic Architecture**. It intentionally avoids passing raw data directly to Large Language Models. Instead, it uses rigorous, deterministic data science (Z-scores, SHAP values, Directed Acyclic Graphs) to build a tightly constrained "cage" of verified evidence. The LLM is only permitted to operate *inside* this mathematically verified cage.

---

## ðŸ§  Neuro-Symbolic Bounding: How Omnision Stops AI Hallucinations

To prevent the AI from making wild, unverified logical leaps, Omnision utilizes strict data structures and mathematical pruning *before* the prompt ever reaches the LLM.

### 1. The A* (Anchor) Anomaly (Ground Zero)
When a KPI breaches its mathematical threshold (either a 3.0 Z-score for mature metrics or a 5% static tripwire for cold-starts), the engine isolates it as the **`AnchorNode`** (A*). Everything in the system centers around A*. It serves as the absolute "Ground Zero" node from which the rest of the causal investigation is rooted.

### 2. The Causal DAG (Graph Construction)
The engine does not pass raw, flat text logs to the LLM. Instead, it constructs a **Directed Acyclic Graph (DAG)** (`kpi_engine/graph/dag_model.py`). It maps rigorous causal edges from the A* node out to Tier 1 (System Logs), Tier 2 (Operational Levers), and Tier 3 (Macro forces). The AI is forced to reason exclusively along these verified edges.

### 3. Dynamic Pruning ("The Cage" & "The Brakes")
The engine ruthlessly cuts out hallucinated "reasons" or irrelevant states dynamically:
*   **The Cage (Temporal & Dimensional Pruning):** The graph builder strictly deletes any candidate log that falls outside a tight `[-48h, +12h]` window of the anomaly. It also prunes states dynamically if dimensional tags (e.g., `region="West"`) do not mathematically intersect with the Anchor.
*   **The Brakes (Weight Pruning):** The configuration enforces an `edge_prune_weight_threshold` (default: `0.65`). If the composite causal weight of an edge drops below this value, that reason is dynamically severed and discarded as "Noise." Traversal depth is also hard-capped (`max_traversal_hops = 2`) to stop infinite logical leaps.

### 4. k-Nearest Neighbors (FAISS Vector RAG)
Instead of relying on the LLM's raw pre-trained memory, the engine uses **FAISS** (Facebook AI Similarity Search) to calculate precise **k-Nearest Neighbors (k-NN)** in high-dimensional embedding spaces (`kpi_engine/memory/vector_store.py`). When the A* anomaly triggers, the vector store performs a nearest-neighbor mathematical search against the institutional playbook. It **only pulls the $k$ nearest historical precedents** and uses their geometric distance to calculate the exact `Contextual Relevance (CR)` score for the DAG.

---

## ðŸŒŸ Enterprise Production Features (v2.0 Extended Edition)

Omnision includes subtle but critical edge-case protections required for live enterprise deployments:

1. **Alert Storm Mitigation (Super-Anchors):** If a systemic failure causes dozens of KPIs to breach simultaneously, Omnision clusters them into a single `Compound_Anchor_Node`. This prevents the system from spawning redundant, expensive LLM swarms, saving compute costs.
2. **External Web Intelligence Agent:** If internal causal evidence is weak, Omnision dynamically invokes an external agent that queries live market data via `yfinance` and runs sentiment analysis using a hosted HuggingFace **FinBERT** API to assess macroeconomic factors.
3. **Feedback Atrophy Protection (Epsilon-Greedy):** When an agent's idea is rejected, its trust score usually decays. To prevent the system from degrading into a rigid, risk-averse echo chamber over time, Omnision shields the creative "Blue-Sky Challenger" agent from penalty decay 5% of the time.
4. **Zero-Day Incidents (Shadow Flag):** If a recommended action originates entirely from the unconstrained Blue-Sky LLM, the system tags it with `requires_shadow_run: true`, forcing RACI owners to sandbox the action before running it in production.
5. **Stale Operational Levers (Liveness Pings):** Before approving an action, the Critic performs a real-time HTTP 200 ping against the target operational endpoint (e.g., AWS, LaunchDarkly). If the endpoint is down, the action is rejected as technically infeasible.

---

## ðŸ›¡ï¸ Enterprise-Grade Security & Privacy

Omnision respects enterprise data boundaries before any data reaches the LLM Swarm:
* **Hybrid Security Matrix (Tier 1 & Tier 2)**: Automatically prunes highly classified entities (e.g., M&A data) or masks financial metrics (`<REDACTED_DOLLAR_VALUE>`) based on the querying user's clearance level.
* **PII Redaction (Simulated Presidio)**: Automatically scans logs and support tickets, redacting Emails, Credit Cards, and SSNs.
* **Behavioral Firewall (Simulated NeMo Guardrails)**: An output scanner intercepts the LLM's recommended actions, hard-blocking destructive commands (e.g., `DROP TABLE`, `rm -rf`).

---

## ðŸš€ Quickstart & Installation

### Prerequisites
* Python 3.9+
* Windows / Linux / macOS compatible.
* No heavy C-compiled dependencies.

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
> 
> 🔒 **Default Login Credentials:**
> * Username: `admin` | Password: `adminpassword` (EXECUTIVE_VP)
> * Username: `engineer` | Password: `engineerpassword` (SENIOR_ENGINEER)
> * Username: `analyst` | Password: `analystpassword` (JUNIOR_ANALYST)
> 
> *To change these passwords or add new users, simply edit the `kpi_engine/users.json` file in your repository!*

### 2. Launch Interactive CLI Demo
```bash
# Run Scenario 1: Stripe Gateway Latency Outage
python run_demo.py --scenario SCENARIO_1_STRIPE_GATEWAY_OUTAGE

# Run Scenario 2: Multivariate Price & Volume Interaction
python run_demo.py --scenario SCENARIO_2_MULTIVARIATE_DAG_SHAP
```

---

## ðŸ¢ Business Setup Guide: Deploying to Your Organization

Omnision is built to be domain-agnostic. Whether you are running a Fintech app, an E-Commerce store, or a Supply Chain logistics network, you can adapt Omnision to automatically manage your business incidents by following these 5 steps:

### Step 1: Hook Up Your Real Data Warehouse (ETL)
By default, the engine uses the `KartMitraDataGenerator` to synthesize fake telemetry for the demo. To use real data:
1. Review the `TelemetryPoint` and `CandidateNode` schemas inside `kpi_engine/data/models.py`.
2. Write a daily cron job, Airflow DAG, or dbt model that queries your internal databases (BigQuery, Snowflake, Datadog) and exports your logs, marketing events, and sales metrics into these exact Pydantic JSON formats.
3. Replace the mock generator call in `kpi_engine/pipeline.py` with a function that loads your live JSON payload.

### Step 2: Define Your Custom KPIs (Semantic Contracts)
The engine needs to know the rules for your specific business metrics.
1. Open `kpi_engine/data/models.py`.
2. Instantiate `KPISemanticContract` objects for your real metrics (e.g., `Cart_Abandonment_Rate`, `API_Latency_P99`).
3. Define the crucial boundaries for each metric: 
   * Set `target_value` (what the metric *should* be).
   * Set `static_tripwire` (e.g., `0.05` means a 5% drop triggers an emergency).
   * Set `graduation_threshold` (how many days of data are needed before it switches from cold-start to Z-score math).

### Step 3: Seed Your Institutional Memory (FAISS Graph-RAG)
To prevent the AI from giving generic advice, you must teach it your company's standard operating procedures (SOPs).
1. Export your past incident post-mortems from Confluence, Jira, or Zendesk.
2. Format them into text documents and pass them into the `PlaybookVectorStore` in `kpi_engine/memory/vector_store.py`.
3. **The Result:** The next time a server crashes or sales dip, Omnision will automatically perform a k-Nearest Neighbor search, retrieve your company's exact past solution, and inject it into the AI prompt as a "Tier 0 Historical Precedent."

### Step 4: Configure Enterprise Security Clearances
1. Open `kpi_engine/scoper/security_matrix.py`.
2. Define what specific logs correspond to different `SecurityTier` classifications (e.g., flag all legal/HR logs as `TIER_1_DOMAIN_PRUNING`).
3. Set your organization's financial limits in `kpi_engine/config.py` (e.g., `vp_approval_required_cost_usd = 100000.0`). The AI will automatically route any proposed fix that costs more than $100k to a VP for manual approval.

### Step 5: Connect Your Cloud / Local LLM
1. Open `kpi_engine/config.py`.
2. Provide your API Keys for your preferred provider. Omnision supports **OpenAI (GPT-4o)**, **Anthropic (Claude 3.5 Sonnet)**, and **Google (Gemini 1.5 Pro)**. 
3. **Data Privacy / No-Leak Deployments:** If your enterprise has strict data privacy rules that prohibit sending logs to public APIs (to prevent accidental data leaks), simply set `llm_provider = "ollama"`. Omnision will automatically route the LangGraph swarm to your privately hosted **Llama 3** instance (via Ollama or vLLM), ensuring zero data ever leaves your servers.
4. Add your `HF_TOKEN` (HuggingFace) if you want the External Web Intelligence Agent to actively scan the stock market and competitor news using FinBERT.
---

## ðŸ“ Mathematical Foundations

Omnision relies on rigorous mathematics before handing data to AI:

1. **Cold-Start Phased Handover**:
   - Phase 1: Static Tripwire
   - Phase 2: Algorithmic Shadowing via EWMA + Surrogate Seasonality overlay
   - Phase 3: Automated Graduation to rolling 30-day Z-score once N >= 30.

2. **Master Multiplicative Composite Weight**:
   W(A*, n_i) = Contextual Relevance x Causal Impact

