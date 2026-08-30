# ⚡ Omnision: Autonomous KPI Storytelling & Causal Governance Engine

![Version](https://img.shields.io/badge/version-3.0%20(v2.0%20Extended)-blue.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-success.svg)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-purple.svg)

**Omnision** is an enterprise-grade autonomous, closed-loop technical architecture that resolves business KPI anomalies. It drives incidents from **Shallow Detection** to **Causal Diagnosis**, **Multi-Layered Solution Synthesis**, **Multi-Agent Governance**, and **Closed-Loop Continuous Learning**.

---

## 🧠 The What, Why, and How

### What is Omnision?
Omnision is a self-governing analytics pipeline. Traditional dashboards (like Tableau or Datadog) simply tell you that a metric is broken. Omnision autonomously investigates *why* it broke, scopes the blast radius, enforces enterprise data security, and deploys a multi-agent LLM swarm to generate a mathematically sound, budget-constrained mitigation plan.

### Why Omnision?
Generative AI often suffers from hallucinations when given raw, unconstrained data. Omnision solves this by using a **Neuro-Symbolic Architecture**. It intentionally avoids passing raw data directly to Large Language Models. Instead, it uses rigorous, deterministic data science (Z-scores, SHAP values, Directed Acyclic Graphs) to build a tightly constrained "cage" of verified evidence. The LLM is only permitted to operate *inside* this mathematically verified cage.

---

## 🔐 Multi-LLM Architecture & RBAC Security (v3.0)

Omnision now features a heavily modular, highly secure dual-node LangGraph orchestration engine designed for zero-leak data deployments.

### 1. Dual-Node Splitting (Primary vs Blue-Sky LLMs)
Omnision breaks the monolithic Swarm into two distinct, parallel AI personas:
* **The Prescriptive RCA Node:** Diagnoses the root cause using standard operating procedures.
* **The Blue-Sky Ideation Node:** Unrestrained, creative shadow-ideation for unconventional fixes.

You can configure **different LLM models for each node simultaneously** via the Streamlit UI (e.g., Use cheap local `Ollama` for standard RCA, but dispatch `GPT-4o` for the complex Blue-Sky creativity).

### 2. Strict Role-Based Access Control (RBAC) & Data Leak Prevention
Omnision enforces severe access controls on the frontend to prevent junior staff from accidentally leaking PII, financial data, or telemetry logs to public cloud providers.
* Only the **`EXECUTIVE_VP`** can authorize and unlock cloud models (OpenAI, Anthropic, Gemini).
* **`SENIOR_ENGINEER`** and **`JUNIOR_ANALYST`** tiers are mathematically hard-locked to local, privately-hosted open-source models like `Ollama` or `mock`.

### 3. Immediate Pre-Flight API Validation
The frontend intercepts and validates the structure of your API keys before running the pipeline. If a key is missing or formatted like garbage (e.g. `your_openai_api_key_here`), it halts execution and safely pops an `API Key Invalid or Not Found` error to the user without crashing the server.

---

## 🔗 Neuro-Symbolic Bounding: How Omnision Stops AI Hallucinations

To prevent the AI from making wild, unverified logical leaps, Omnision utilizes strict data structures and mathematical pruning *before* the prompt ever reaches the LLM.

### 1. The A* (Anchor) Anomaly (Ground Zero)
When a KPI breaches its mathematical threshold, the engine isolates it as the **`AnchorNode`** (A*). Everything in the system centers around A*. It serves as the absolute "Ground Zero" node from which the rest of the causal investigation is rooted.

### 2. The Causal DAG (Graph Construction)
The engine does not pass raw, flat text logs to the LLM. Instead, it constructs a **Directed Acyclic Graph (DAG)** (`kpi_engine/graph/dag_model.py`). It maps rigorous causal edges from the A* node out to Tier 1, Tier 2, and Tier 3 dependencies. The AI is forced to reason exclusively along these verified edges.

### 3. Dynamic Pruning ("The Cage" & "The Brakes")
The engine ruthlessly cuts out hallucinated "reasons" or irrelevant states dynamically:
*   **The Cage (Temporal & Dimensional Pruning):** The graph builder strictly deletes any candidate log that falls outside a tight `[-48h, +12h]` window. It also prunes states dynamically if dimensional tags (e.g., `region="West"`) do not mathematically intersect with the Anchor.
*   **The Brakes (Weight Pruning):** The configuration enforces an `edge_prune_weight_threshold` (default: `0.65`). If the composite causal weight of an edge drops below this value, that reason is dynamically severed and discarded as "Noise." Traversal depth is also hard-capped (`max_traversal_hops = 2`) to stop infinite logical leaps.

### 4. k-Nearest Neighbors (FAISS Vector RAG)
Instead of relying on the LLM's raw pre-trained memory, the engine uses **FAISS** to calculate precise **k-Nearest Neighbors (k-NN)** in high-dimensional embedding spaces (`kpi_engine/memory/vector_store.py`). It **only pulls the $k$ nearest historical precedents** and uses their geometric distance to calculate the exact `Contextual Relevance (CR)` score for the DAG.

---

## 🚀 Quickstart & Installation

### Prerequisites
* Python 3.9+
* Windows / Linux / macOS compatible.
* No heavy C-compiled dependencies.

### Installation
```bash
git clone https://github.com/your-org/omnision.git
cd omnision
pip install -r requirements.txt
pip install langchain-ollama # Required for local, zero-leak privacy mode
```

### 1. Launch Interactive Web Dashboard (Streamlit)
```bash
streamlit run app.py
```
> Opens in your browser at `http://localhost:8501`.
> 
> 🔒 **Default Login Credentials:**
> * Username: `admin` | Password: `adminpassword` (EXECUTIVE_VP) - *Can use all LLMs*
> * Username: `engineer` | Password: `engineerpassword` (SENIOR_ENGINEER) - *Restricted to Ollama*
> * Username: `analyst` | Password: `analystpassword` (JUNIOR_ANALYST) - *Restricted to Ollama*
> 
> *To change these passwords or add new users, simply edit the `kpi_engine/users.json` file in your repository!*

---

## 🛠️ Configuring API Keys

Omnision supports OpenAI, Anthropic, Gemini, and local Ollama models. 
You must configure your API keys in **`kpi_engine/config.py`**. 

1. Open `kpi_engine/config.py` in your code editor.
2. Locate the `Config` dataclass at the top of the file.
3. Paste your specific keys exactly between the quotation marks.

```python
@dataclass
class Config:
    # 🔑 PASTE YOUR API KEYS HERE:
    openai_api_key: str = "sk-..." 
    anthropic_api_key: str = "sk-ant-..."
    google_api_key: str = "..."
    
    # 🦙 OLLAMA SETTINGS (For 100% Private Data)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
```
*(Note: If you already have these set as system Environment Variables (e.g., `OPENAI_API_KEY`), Omnision will automatically detect and use them!)*

---

## 🏢 Business Setup Guide: Deploying to Your Organization

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

### Step 5: Start the LangGraph Orchestrator
Once your keys and KPIs are wired up, you can start the dashboard using `streamlit run app.py` and manage your operations entirely autonomously.
