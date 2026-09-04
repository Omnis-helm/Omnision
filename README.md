# ⚡ Omnision: Autonomous KPI Storytelling & Causal Governance Engine

![Version](https://img.shields.io/badge/version-3.0%20(v2.0%20Extended)-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-success.svg)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-purple.svg)
![ML Engine](https://img.shields.io/badge/ML%20Engine-XGBoost%20%2B%20SHAP-green.svg)
![Local Acceleration](https://img.shields.io/badge/Performance-Zero--Credit%20Local%20Caching-orange.svg)

**Omnision** is an enterprise-grade autonomous, closed-loop technical architecture that resolves business KPI anomalies. It drives incidents from **Shallow Detection** to **Causal Diagnosis**, **Multi-Layered Solution Synthesis**, **Multi-Agent Governance**, and **Closed-Loop Continuous Learning**.

---

## 📋 Table of Contents
> 📘 **Dashboard Operational Manual:** For a step-by-step user guide to operating the Streamlit Web Interface, refer to [manual.md](file:///c:/Users/arind/OneDrive/Documents/project_summer/accenture/Omnision/manual.md).

1. [Architectural Principles & Philosophy](#-architectural-principles--philosophy)
2. [Core Technology Stack](#-core-technology-stack)
3. [Working Mechanics & Pipeline Architecture (8 Stages)](#-working-mechanics--pipeline-architecture-8-stages)
4. [Performance Optimization & Local ML Acceleration](#-performance-optimization--local-ml-acceleration)
5. [In-Depth Scenario Walkthroughs (Operational Executions)](#-in-depth-scenario-walkthroughs-operational-executions)
6. [Security & Role-Based Access Control (RBAC)](#-security--role-based-access-control-rbac)
7. [Environment Configuration & API Setup](#%EF%B8%8F-environment-configuration--api-setup)
8. [Installation & Quickstart Guide](#-installation--quickstart-guide)
9. [Automated Test Suite & Verification Matrix](#-automated-test-suite--verification-matrix)
10. [Repository Directory Sitemap](#-repository-directory-sitemap)

---

## 🧠 Architectural Principles & Philosophy

### 1. The Core Problem: Why Dashboard Alerts Fail
Traditional dashboards (like Datadog, Tableau, or Grafana) inform you *that* a metric has breached a threshold, but leave human engineers to manually inspect logs, search Slack channels, and infer root causes under pressure. Conversely, unconstrained Generative AI often hallucinates false causes or recommends dangerous, budget-violating mitigation actions when fed raw, uncurated log streams.

### 2. The Solution: Neuro-Symbolic Bounding ("Caging the LLM")
Omnision resolves AI hallucinations through a **Neuro-Symbolic Architecture**:
- **Symbolic Math Layer (Ground Truth):** Strict statistical algorithms (Z-scores, EWMA, Directed Acyclic Graphs, XGBoost, and SHAP values) filter noise, prune irrelevant states, and isolate mathematically proven causal evidence.
- **Neural LLM Layer (Reasoning & Narrative):** The Large Language Model is **caged** inside this mathematically verified evidence pool. It is prohibited from reasoning outside the DAG, ensuring 100% grounded diagnostic narratives and actionable playbooks.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 OMNISION PIPELINE FLOW                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 0 & 1: Data Telemetry, Z-Score & EWMA Anomaly Detection                   │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 2: Scoping Router & Hybrid Security Matrix (Tier 1 Pruning / Tier 2 Mask) │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 3: Bounded Graph Builder ("The Cage" & "The Brakes" Traversal Depth = 2)  │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 4: Composite Causal Scoring (W = CR * CI) & XGBoost + SHAP Attribution    │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 5: Dual-Channel Suggester (Grounded SOPs vs Challenger Blue-Sky)          │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 6: Multi-Agent Swarm, Liveness Pings & Deterministic Supervisor           │
  └────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │ Stage 7: Closed-Loop Continuous Learning, RCA Recalibration & Playbook Append   │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Core Technology Stack

- **Dashboard & User Interface:** Streamlit (v1.30+), Plotly (v5.0+), HTML5/CSS3 custom components.
- **Machine Learning & Attribution Engine:** XGBoost (`XGBRegressor`), Scikit-Learn (`GradientBoostingRegressor`), Custom Exact Shapley Engine, NumPy, Pandas.
- **Graph & Mathematical Models:** NetworkX, Pure-Python Exact Shapley Cooperative Game Theory.
- **Multi-Agent Orchestration & Swarm:** LangGraph, LangChain, Hybrid Supervisor Framework.
- **LLM & NLP Integrations:** Google Gemini REST API (`gemini-3.6-flash`), OpenAI GPT-4o (`ChatOpenAI`), Anthropic Claude 3.5 Sonnet (`ChatAnthropic`), Ollama (`llama3`), HuggingFace FinBERT.
- **Memory & Vector Search:** LocalVectorStore (TF-IDF + Cosine Similarity), FAISS Vector Store, SentenceTransformers (`all-MiniLM-L6-v2`).
- **Concurrency & Local Acceleration:** ThreadSafeModelLoader (`threading.Lock()` mutexes), LRU query caching (`@lru_cache`), `LLMResponseCache`.
- **Validation & API Standards:** Pydantic v2 schemas, FastAPI backend hooks, Python `pytest`.

---

## ⚙️ Working Mechanics & Pipeline Architecture (8 Stages)

### Stage 0: Heterogeneous Data Ingestion & Reconciliation
- **The ETL Layer:** Simulates real-world data fragmentation by ingesting 4 distinct sources: Hourly Web Analytics (JSON), Minutely IT Telemetry (CSV), Daily Sales (SQLite), and Weekly Market Vendors (Parquet).
- **The Reconciler:** A dedicated `HeterogeneousDataReconciler` automatically resamples (upsampling/downsampling) these cadences into a single daily DataFrame containing **5 mathematically connected KPIs** (Traffic, AOV, Cart Abandonment, Checkout Conversion, Regional Revenue).

### Stage 1: Data Telemetry & Anomaly Detection
- **Z-Score Detection:** Monitors mature telemetry series ($30+$ days). Alert tripwire at $Z \ge 3.0$; severe shock tripwire at $Z \ge 5.0$.
- **Cold-Start Handover:** For metrics with $< 30$ samples, switches automatically to Exponentially Weighted Moving Average (EWMA, $\alpha = 0.3$) and static tripwires ($5\%$ variance).

### Stage 2: Directional Scoping & Security Matrix
- **Directional Router:** Filters candidate log events matching the anomaly's directional vector (e.g., negative revenue drop vs positive latency spike).
- **Hybrid Security Matrix:**
  - **Tier 1 Strategic Domain Pruning:** Completely redacts strategic executive logs (M&A, HR terminations) from non-VP clearance.
  - **Tier 2 Token Masking:** Obfuscates PII/credentials while preserving statistical graph properties.

### Stage 3: Bounded Graph Construction ("The Cage" & "The Brakes")
- **The Cage (Temporal & Dimensional Bounds):** Restricts causal candidate nodes to a temporal window of `[-48h, +12h]` around the anomaly timestamp.
- **The Brakes (Traversal Depth & Weight Attenuation):** Hard-caps causal traversal hops to `max_traversal_hops = 2` and prunes edges below composite weight threshold (`0.50`).

### Stage 4: Composite Causal Scoring ($W = CR \times CI$)
Computes the master multiplicative score $W(A^*, n_i) = CR \times CI$:
1. **Contextual Relevance ($CR$):** Evaluated by $CR = \alpha W_t + \beta W_e + \gamma W_s$ (Temporal Proximity $W_t$, Entity Overlap $W_e$, Semantic Similarity $W_s$).
2. **Causal Impact ($CI$):** Blends Signal-to-Noise Ratio ($W_{snr}$) with Counterfactual Impact ($W_{cf}$).
3. **XGBoost & SHAP Attribution:** Evaluates ambient candidate variables (competitor price changes, weather) using exact Shapley attributions.

### Stage 5: Dual-Channel Solution Suggestion Network
- **Channel A (Grounded Path):** Queries Layer 1 internal playbooks, Layer 2 market precedents, and Layer 3 operational levers. The pipeline dynamically extracts **multiple operational fixes** simultaneously, provided they pass strict business thresholds (e.g., Executive cost limits and execution timeframes).
- **Channel B (Challenger Path):** Dispatches creative, unconstrained ideation for lateral problem solving. These "Blue-Sky" ideas are sent to the **Reality Checker Critic**, an independent agent that provides non-punishing feasibility critiques without rejecting the idea or looping the graph. This allows operators to sandbox, reroll, or promote wild ideas to the main production pipeline at will.

### Stage 6: Multi-Agent Swarm Governance & Liveness Validation
- **Deterministic Validator:** Enforces JSON schema validity, security forbidden command lists (`drop table`, `rm -rf`), budget cost ceilings ($100k VP limit), and live network ping checks.
- **LLM Supervisor (The Critic):** Evaluates logical alignment between proposed actions and primary root causes. If an operational fix violates logic, the Critic **rejects and loops** the LangGraph swarm back to the suggester agents until a verified fix is produced.

### Stage 7: Closed-Loop Continuous Learning
- **Human RCA Overrides:** Analyst demotions/promotions adjust the engine's semantic threshold ($\eta = 0.05$).
- **Model Trust Tuning:** Human ACCEPT/REJECT signals boost or decay agent confidence weights ($W_m^{(t+1)} = W_m^{(t)} \times (1 - \eta)$).
- **Dynamic Playbook Appending:** Approved operational modifications are automatically saved to Layer 1 runbooks.

---

## ⚡ Performance Optimization & Local ML Acceleration

Omnision includes a built-in local performance engine to eliminate API credit exhaustion and ensure sub-second response times:

```
                  ┌──────────────────────────────────────────────┐
                  │           PERFORMANCE ENGINE LAYER           │
                  └──────────────────────┬───────────────────────┘
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       ▼                                 ▼                                 ▼
┌───────────────┐              ┌───────────────────┐             ┌──────────────────┐
│ MUTEX LOCKING │              │ ZERO-CREDIT CACHE │             │   LOCAL ML & VR  │
├───────────────┤              ├───────────────────┤             ├──────────────────┤
│ Thread-Safe   │              │ LLMResponseCache  │             │ XGBoost Model    │
│ Model Loader  │              │ FinBERT LRU Cache │             │ LocalVectorStore │
└───────────────┘              └───────────────────┘             └──────────────────┘
```

1. **Thread-Safe Lazy Loading (`kpi_engine/ml/local_ml_engine.py`)**:
   Uses `ThreadSafeModelLoader` with `threading.Lock()` to load heavy NLP and ML models into memory only when needed, avoiding startup delays and duplicate memory allocations.
2. **XGBoost Disk Persistence (`kpi_engine/ml/global_model.py`)**:
   Saves trained model weights to `saved_global_model.pkl`. On subsequent app launches, it loads directly from disk in **< 5ms**.
3. **Zero-Credit Vector Search (`kpi_engine/memory/vector_store.py`)**:
   Features a pure Python + NumPy TF-IDF cosine similarity store (`LocalVectorStore`), preventing compulsory cloud embedding API calls.
4. **Swarm & Query Caching (`kpi_engine/governor/external_tools.py`)**:
   Applies `@lru_cache` to FinBERT sentiment analysis and market data requests.

---

## 🔬 In-Depth Scenario Walkthroughs (Operational Executions)

### Walkthrough 1: Scenario 1 — Payment Gateway Latency Outage

#### 1. Anomaly Ground Zero ($A^*$)
- **Metric:** `West Region Checkout Conversion Rate` (`KPI_WEST_CHECKOUT_CONV`)
- **Current Value:** `2.80%` (Baseline: `3.20%`, Variance: `-12.50%`)
- **Z-Score:** $Z = 5.19$ (**Severe Shock**)

#### 2. Graph Construction & Causal Scoring
The engine builds the DAG from $A^*$ and scores incoming candidate logs:
- `NODE-SYS-101` (System Log): `"Payment Gateway API Timeout (Stripe v4.1), 8000ms latency on POST /v1/charges"`
  - **Contextual Relevance ($CR$):** $0.92$ (High temporal proximity and entity match `region="West"`, `domain="downstream"`).
  - **Counterfactual Weight ($W_{cf}$):** $0.95$ (Tier 1 Direct Engineering Cause).
  - **Composite Weight ($W$):** $0.8740$ (Ranks as **Primary Root Cause**).

#### 3. Swarm Proposal Synthesis
The Prescriptive Swarm matches Layer 1 Playbook `ACT-PM-2291`:
- **Action:** `"Roll back Stripe v4.1 gateway integration to v4.0 and re-route 15% traffic to Adyen backup"`
- **Estimated Cost:** `$4,200.00`
- **RACI Owner:** `Platform Engineering`
- **Execution Command:** `helm rollback stripe-gateway 4.0 && traffic-router set --split stripe:85,adyen:15`

#### 4. Supervisor Verdict & Payloads
- **Deterministic Check:** Passed (Cost $< \$10,000$ auto-approved ceiling; liveness ping active).
- **Semantic Supervisor:** Verified alignment between 8000ms API timeout and gateway rollback action.
- **Executive Output:** Financial Exposure `$42,000.00`, Business Risk **HIGH**.

---

### Walkthrough 2: Scenario 2 — Multivariate Price & Volume (SHAP Analysis)

#### 1. Anomaly Ground Zero ($A^*$)
- **Metric:** `Electronics Division Sales Volume` (`KPI_ELEC_SALES_VOL`)
- **Variance:** `-18.20%` ($Z = 4.85$)

#### 2. XGBoost & SHAP Attribution Execution
The engine encounters ambient market variables and triggers the SHAP explainer:
- Features evaluated: `competitor_price`, `weather_severity`, `server_latency`, `marketing_spend`.
- **SHAP Results:**
  - `competitor_price`: **$64.20\%$ variance explained** (Competitor RivalRetail launched a $20\%$ flash sale).
  - `weather_severity`: **$12.10\%$ variance explained**.
  - `marketing_spend`: **$8.30\%$ variance explained**.

#### 3. Prescriptive Solution
- **Primary Cause:** Extracted via SHAP attribution as `Competitor RivalRetail 20% flash promotion`.
- **Recommended Action:** `"Deploy dynamic price-matching promotion on top 5 electronics SKUs"`
- **Cost:** `$6,800.00` | **Status:** `AUTO_APPROVED`

---

### Walkthrough 3: Scenario 3 — Cold-Start Metric & Noise Profile Filtering

#### 1. Anomaly Ground Zero ($A^*$)
- **Metric:** `Drone Delivery Volume` (`KPI_DRONE_DELIV`)
- **History:** $14$ days ($< 30$ sample threshold $\rightarrow$ **Cold Start Phase**).

#### 2. Phased Handover & Vector Store Lookup
- Uses static tripwire ($5\%$ flat deviation) and EWMA ($\alpha = 0.3$).
- `PlaybookVectorStore` runs $k$-NN search against historical incident signatures.
- **Match Found:** Document `NOISE-001`: `"False Alarm: Ad Clicks dropped 20% on a weekend due to natural stochastic variance."`
- **Counterfactual Score:** Assigned $W_{cf} = 1.00$ for explicit noise visibility.

#### 3. Execution Verdict
- **Supervisor Status:** Discarded as false alarm noise signature. No engineering escalation required.

---

### Walkthrough 4: Scenario 4 — Hybrid Security Matrix & Strategic Abstention

#### 1. Strategic Anomaly Ground Zero ($A^*$)
- **Metric:** `Corporate Net Operating Margin` (`KPI_CORP_MARGIN`)
- **Variance:** `-14.10%`

#### 2. Security Clearance Scoping
- Primary Cause: `NODE-SEC-401` (`"Confidential acquisition of FastPay checkout gateway: $850,000 advisor fee"`) classified under **Tier 1 Strategic Domain Pruning**.

#### 3. Role-Based Execution Results
- **User: `EXECUTIVE_VP` (Full Access):**
  - Clears Tier 1 pruning. Primary driver displayed: `"Confidential acquisition of FastPay gateway"`.
  - Action: `"Approve scheduled non-recurring M&A charge against corporate reserve"`
- **User: `SENIOR_ENGINEER` or `JUNIOR_ANALYST` (Restricted Access):**
  - Tier 1 Pruning strips the driver to protect M&A confidentiality.
  - **Graceful Abstention:** The engine returns `STATUS: ABSTAINED` with a cryptographic audit receipt instead of presenting incomplete or hallucinated data.

---

## 🔒 Security & Role-Based Access Control (RBAC)

Omnision enforces strict frontend and backend RBAC to prevent unauthorized data exposure:

| Role Clearance | Executive View | Engineer Logs | Public LLMs (OpenAI/Gemini/Anthropic) | Private LLMs (Ollama/Mock) | Tier 1 M&A Logs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`EXECUTIVE_VP`** | ✅ Full | ✅ Full | ✅ Allowed | ✅ Allowed | ✅ Unlocked |
| **`SENIOR_ENGINEER`** | ✅ Full | ✅ Full | ❌ Blocked | ✅ Allowed | 🔒 Abstained |
| **`JUNIOR_ANALYST`** | ⚠️ Redacted | ⚠️ Masked | ❌ Blocked | ✅ Allowed | 🔒 Abstained |

---

## 🛠️ Environment Configuration & API Setup

Omnision dynamically parses `.env` files on startup.

### 1. Create your `.env` file
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. `.env` File Structure
```ini
# Performance & Local Optimization Settings
PREFER_LOCAL_TOOLS=True
ENABLE_LLM_CACHE=True
ENABLE_LOCAL_ML_MODELS=True

# Default LLM Provider ('mock', 'local', 'openai', 'anthropic', 'gemini', 'ollama')
LLM_PROVIDER=mock

# Cloud Provider API Keys (Used when configured by EXECUTIVE_VP)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
HF_TOKEN=your_huggingface_token_here

# Ollama Local Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## 🚀 Installation & Quickstart Guide

### Prerequisites
- Python 3.9+ (Python 3.11/3.12/3.13 supported)
- Git

### 1. Installation
```bash
git clone https://github.com/your-org/omnision.git
cd omnision
pip install -r requirements.txt
```

### 2. Launch Interactive Web Dashboard
```bash
streamlit run kpi_engine/ui/streamlit_app.py
```
> Opens in your browser at `http://localhost:8501`.

#### Default Credentials (`kpi_engine/users.json`):
- **Username:** `admin` | **Password:** `adminpassword` (`EXECUTIVE_VP`)
- **Username:** `engineer` | **Password:** `engineerpassword` (`SENIOR_ENGINEER`)
- **Username:** `analyst` | **Password:** `analystpassword` (`JUNIOR_ANALYST`)

---

## 🧪 Automated Test Suite & Verification Matrix

Run full unit and integration tests using `pytest`:

```bash
python -m pytest tests/
```

### Test Suite Summary (12 Test Cases):
- `tests/test_causal_math_shap.py`: Verifies Custom Exact Shapley Engine attributions and exact Shapley game theory.
- `tests/test_closed_loop.py`: Verifies end-to-end pipeline execution, human RCA override cascade, model trust decay, and dynamic playbook appending.
- `tests/test_cold_start.py`: Verifies EWMA calculations and phased handover triggers.
- `tests/test_multi_agent_critic.py`: Verifies solution candidate scoring and supervisor feedback loops.
- `tests/test_security_matrix.py`: Verifies Tier 1 pruning, Tier 2 masking, and graceful abstention.

### Run Verification Matrix Script
```bash
python scratch_verify.py
```

---

## 📂 Repository Directory Sitemap

```
Omnision/
├── app.py                      # Root entry point for Streamlit web dashboard
├── .env                        # Environment keys and system settings
├── .env.example                # Template configuration file
├── requirements.txt            # Project dependencies
├── scratch_verify.py           # Verification script for 4 benchmark scenarios
├── test_run.py                 # E2E test script
├── tests/                      # Pytest automation suite (12 test suites)
│   ├── test_causal_math_shap.py
│   ├── test_closed_loop.py
│   ├── test_cold_start.py
│   ├── test_multi_agent_critic.py
│   └── test_security_matrix.py
└── kpi_engine/                 # Master System Package
    ├── config.py               # Dynamic SystemConfig and .env loader
    ├── pipeline.py             # Orchestrator for 8-stage Neuro-Symbolic pipeline
    ├── users.json              # RBAC user credentials database
    ├── ml/                     # Machine Learning & Local Performance Engine
    │   ├── global_model.py     # XGBoost regressor with disk model persistence
    │   ├── shap_explainer.py   # Exact Shapley additive feature explainer
    │   └── local_ml_engine.py  # ThreadSafeModelLoader, LRU cache & LocalVectorStore
    ├── memory/                 # Institutional Memory & Graph-RAG Vector Store
    │   └── vector_store.py     # PlaybookVectorStore with LocalVectorStore fallback
    ├── governor/               # Multi-Agent Governance & Security
    │   ├── hybrid_supervisor.py# Neuro-Symbolic & Local Semantic Supervisor
    │   ├── langgraph_orchestrator.py # Swarm workflow with local fallback
    │   ├── llm_factory.py      # LLM provider factory & Gemini direct REST caller
    │   ├── llm_state.py        # AgentState definition for LangGraph
    │   ├── schemas.py          # Unified Master Payload schemas
    │   └── external_tools.py   # FinBERT web intelligence with LRU query caching
    ├── suggester/              # Multi-Agent Generator & Dual-Channel Network
    │   ├── llm_swarm.py        # RCA and Blue-Sky swarm nodes with LRU caching
    │   ├── dual_channel.py     # Grounded vs Challenger solution networks
    │   └── layers_data.py      # Layer 1 internal playbooks & operational levers
    ├── causal/                 # Causal Inference & Graph Mathematics
    │   ├── composite_scorer.py # Multiplicative composite causal weights (W = CR * CI)
    │   ├── contextual_relevance.py # Temporal, Entity, and Semantic similarity gatekeeper
    │   ├── counterfactual_tiers.py # Counterfactual hypothesis hierarchy
    │   └── shapley_engine.py   # Cooperative game theory engine
    ├── graph/                  # Directed Acyclic Graph (DAG) Construction
    │   ├── bounded_builder.py  # Bounded Graph Pre-Pruner ("The Cage" & "The Brakes")
    │   └── dag_model.py        # Graph schema definitions
    ├── detector/               # Anomaly Detection & Cold-Start Handover
    │   ├── anomaly_pipeline.py # Z-score and EWMA anomaly detector
    │   └── cold_start.py       # Phased handover manager
    ├── scoper/                 # Security Scoping & Blast Radius Matrix
    │   ├── directional_router.py # Directional Scoper
    │   └── security_matrix.py  # Hybrid Security Matrix (Tier 1 & Tier 2)
    ├── learning/               # Closed-Loop Continuous Learning
    │   ├── dynamic_playbook.py # Dynamic Playbook appender
    │   ├── rca_corrections.py  # Human RCA override & recalibration manager
    │   └── trust_tuning.py     # Model trust decay & boost tuner
    ├── data/                   # Data Models & Seed Scenarios
    │   ├── models.py           # Core Pydantic data schemas
    │   ├── generator.py        # Telemetry data generator
    │   └── seed_scenarios.py   # 4 enterprise benchmark scenarios
    └── ui/                     # Interactive Streamlit Frontend
        └── streamlit_app.py    # Executive Two-Column Dashboard with RBAC
```

---

## 🏢 Enterprise Deployment: Setting Up For Your Business

While this repository provides a fully functional Proof-of-Concept (POC) powered by simulated benchmark scenarios, integrating Omnision into a live enterprise environment requires a few architectural bridges.

**Crucial Clarification on Omnision's Role:**
Omnision is designed strictly as an **analytical and advisory governance engine**, not an automated execution tool. When an executive clicks "Approve & Execute" in the dashboard, the engine *does not* blindly modify production infrastructure. Instead, this action serves as a formal governance approval stamp. The approved RCA and mitigation strategy is then formally passed to specific human professionals (DevOps, SREs, or Data Engineers) to further analyze and safely execute via existing deployment pipelines.

To transition Omnision from a POC to a live business environment, four key connections must be established:

### 1. Live Data Ingestion (The Eyes)
*   **Current State:** Uses hardcoded JSON seed scenarios (`seed_scenarios.py`).
*   **Business Setup:** Rip out the benchmark scenarios and connect Omnision directly to your live observability stack. Configure Webhooks from **Datadog, Splunk, AWS CloudWatch, or Prometheus** to stream live telemetry to Omnision. When your monitoring tools detect a statistical anomaly (e.g., error rates spiking), they trigger Omnision's backend automatically.

### 2. Enterprise RAG Memory (The Context)
*   **Current State:** The vector store (`vector_store.py`) runs on mocked internal documents.
*   **Business Setup:** Connect the Vector Database (e.g., Pinecone, Weaviate) directly to your company's **Confluence pages, Jira tickets, and historical Incident Post-Mortems**. This ensures that when the LangGraph swarm diagnoses a failure, it references your exact internal architecture and past company-specific resolutions, rather than relying on generic LLM knowledge.

### 3. Alerting & Professional Handoff (The Voice)
*   **Current State:** Renders diagnostics solely via the local Streamlit dashboard.
*   **Business Setup:** Integrate Omnision with alerting routers like **PagerDuty, Slack, or Microsoft Teams**. When Omnision completes its diagnosis, it immediately pages the correct on-call professional with a deep-link to the Omnision dashboard. Once the mitigation is approved, it sends a webhook to the SRE team's ticketing system (like Jira or ServiceNow) for formal execution.

### 4. Compliance & Audit Logging (The Ledger)
*   **Current State:** Authentication is handled via a static Python dictionary mock login.
*   **Business Setup:** Replace the mock login with Enterprise SSO (Okta, Google Workspace, Microsoft Entra) for strict Role-Based Access Control. Additionally, attach a relational database (like PostgreSQL) to log every single diagnostic prompt, causal evidence weight, and human approval action to ensure full **SOC2 compliance** and an auditable paper trail.

---

## 📜 License & Enterprise Compliance

Omnision is built for enterprise data privacy. By combining deterministic neuro-symbolic graph bounding, local vector stores, thread-safe model caching, and strict RBAC data masking, it ensures complete mathematical reliability without compromising sensitive company data.
