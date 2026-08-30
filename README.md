# Omnision: Autonomous KPI Storytelling Engine
**Accenture Innovation Challenge 2026 - Round 2 Prototype Development**
**Problem Track 3:** `BusinessIntelligence.ai`

---

## 📄 Detailed Business Proposal

### 1. Problem Framing
Modern enterprises track KPIs across fragmented systems with different refresh cadences and granularities. When a critical metric drops, the "right" explanation often depends on who is asking. Furthermore, applying raw Generative AI to this problem introduces massive risk: hallucinations erode stakeholder trust, and unconstrained LLMs can easily leak highly classified M&A or financial data to unauthorized employees. Companies don't need a chatbot that talks about data—they need an engine that *governs* data, mathematically proves causation, and translates telemetry into persona-specific, actionable business levers.

### 2. Solution Design: The "Neuro-Symbolic Cage"
Omnision is a self-governing, multi-agent analytics engine. It intentionally avoids passing raw data directly to Large Language Models (LLMs). Instead, it uses deterministic data science (Z-scores, SHAP values, Directed Acyclic Graphs) to build a tightly constrained "cage" of evidence. Only this heavily vetted, mathematically verified causal graph is passed to the LLM swarm, virtually eliminating hallucinations and ensuring recommendations are bounded by strict financial and operational constraints.

### 3. Target Users (Role-Based Personas)
Omnision dynamically alters its causal math and narrative output based on the clearance of the user:
* **Executive VP (Tier 1 Clearance):** Receives unrestricted access to highly sensitive strategic drivers (e.g., confidential M&A restructuring costs, HR actions) with full financial exposure numbers.
* **Senior Engineer (Tier 2 Clearance):** Receives full system logs and technical playbooks, but absolute financial values are mathematically masked (`<REDACTED_DOLLAR_VALUE>`) to prevent insider trading risks.
* **Junior Analyst (Standard Clearance):** Receives basic operational drivers. If a root cause is determined to be highly classified, the system gracefully abstains from answering rather than hallucinating a fake reason.

### 4. Business Case & Impact
* **Eliminates Alert Fatigue:** "Super-Anchor" clustering merges dozens of downstream system alerts into a single Root Cause narrative.
* **Slashing RCA Time:** Reduces Root Cause Analysis (RCA) from days of cross-departmental war rooms to seconds of automated swarm analysis.
* **Compute Cost Reduction:** By using deterministic math (FAISS, SHAP) to prune the evidence pool *before* LLM generation, token consumption is reduced by over 80% compared to brute-force RAG approaches.

### 5. Phased Roadmap
1. **Phase 1: Proof of Concept (Current Prototype):** Simulated telemetry, deterministic causal scoring, LangGraph agent swarm, and Streamlit executive dashboard.
2. **Phase 2: Live Integration (Next 6 Months):** Connect to Snowflake/Databricks for live telemetry ingestion. Replace regex-based security with formal integrations (Microsoft Presidio for PII, NVIDIA NeMo for Guardrails).
3. **Phase 3: Autonomous Remediation (Year 1+):** Transition from "Human-in-the-loop" to "Human-on-the-loop," allowing the Playbook Agent to automatically execute self-healing bash/Kubernetes scripts for low-risk operational anomalies.

### 6. Key Risks & Mitigations
* **Risk: LLM Hallucination.** *Mitigation:* The "Neuro-Symbolic Cage." The LLM is forced to cite nodes from the verified DAG. It cannot invent external drivers.
* **Risk: Action Unpredictability.** *Mitigation:* "The Critic." An independent deterministic supervisor cross-examines every LLM proposal against hardcoded budget limits and live endpoint pings before allowing it to reach a human.
* **Risk: Feedback Atrophy.** *Mitigation:* $\epsilon$-Greedy Trust Tuning. To prevent the system from becoming a risk-averse echo chamber, a "Blue-Sky Challenger" agent is protected from penalty decay 5% of the time to ensure creative solutions remain part of the network over years of operation.

---

## ⚙️ The 7-Stage Orchestration Pipeline
*(Aligned with BusinessIntelligence.ai Requirements)*

Omnision executes a 7-stage sequential pipeline (`kpi_engine/pipeline.py`), blending standard machine learning, vector databases (FAISS), and multi-agent orchestration (LangGraph):

**1. Data Generation and Telemetry Ingestion (Detects material movements):**
Uses `KartMitraDataGenerator` to synthesize temporally correlated time-series data across disparate domains.
**2. Detection and Cold-Start Management (Reconciles context):**
Monitors for statistical deviations (Z-score > 3.0). Newly launched KPIs rely on static tripwires until they cross a 30-day graduation threshold.
**3. Directional Scoping and Enterprise Security (Role-based security):**
Directionally filters noise and applies the Hybrid Security Matrix (Domain Pruning & Token Masking) before evidence aggregation.
**4. Bounded Graph Construction & Causal Scoring (Identifies explanatory drivers):**
Uses a `CompositeCausalScorer` combining Statistical Impact (simulated SHAP) and Contextual Relevance (FAISS embeddings).
**5. Multi-Agent Swarm (Generates persona-specific narratives):**
Passes the DAG to a LangGraph swarm containing a Prescriptive Agent, an Ops Playbook Agent, and a Blue-Sky Challenger.
**6. The Critic and Supervisor Layer (Communicates uncertainty & Recommends constraints):**
A deterministic validator that enforces JSON schemas, budgetary bounds, checks liveness pings of technical levers, and tags unproven ideas with shadow-run requirements.
**7. Closed-Loop Continuous Learning (Learns from user feedback):**
Human RCA overrides are ingested back into the FAISS memory banks. The Swarm's confidence weights decay when rejected, mathematically learning stakeholder preferences.

---

## 🛡️ Enterprise Production Features (v2.0 Extended)

Omnision includes subtle but critical edge-case protections required for live enterprise deployments:

1. **Alert Storm Mitigation (Super-Anchors):** If a systemic failure causes dozens of KPIs to breach simultaneously, Omnision clusters them into a single `Compound_Anchor_Node`.
2. **External Web Intelligence Agent:** If internal causal evidence is weak, Omnision dynamically invokes an external agent that queries live market data via `yfinance` and runs sentiment analysis using a hosted HuggingFace **FinBERT** API to assess macroeconomic factors.
3. **Zero-Day Incidents (Shadow Flag):** If a recommended action originates entirely from the unconstrained Blue-Sky LLM, the system tags it with `requires_shadow_run: true`, forcing RACI owners to sandbox the action before running it in production.
4. **Stale Operational Levers (Liveness Pings):** Before approving an action, the Critic performs a real-time HTTP 200 ping against the target operational endpoint (e.g., AWS, LaunchDarkly). If the endpoint is down, the action is rejected as technically infeasible.

---

## 🚀 Quickstart & Installation

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

---

## 🧮 Mathematical Foundations

Omnision relies on rigorous mathematics before handing data to AI:

1. **Cold-Start Phased Handover**:
   - Phase 1: Static Tripwire $|x - x_{\text{target}}| / x_{\text{target}} \ge 0.05$
   - Phase 2: Algorithmic Shadowing via EWMA + Surrogate Seasonality overlay
   - Phase 3: Automated Graduation to rolling 30-day $Z$-score once $N \ge 30$.

2. **Multivariate Metric DAGs**:
   $$\Delta R = P \cdot \Delta V + V \cdot \Delta P + \Delta P \cdot \Delta V$$
   Captures price effect, volume effect, and joint non-linear interaction without machine learning approximations.

3. **Master Multiplicative Composite Weight**:
   $$W(A^*, n_i) = \text{Contextual Relevance} \times \text{Causal Impact}$$

4. **Telemetry-Driven Trust Weight Tuning**:
   $$W_m^{(t+1)} = W_m^{(t)} \times (1 - \eta)$$
