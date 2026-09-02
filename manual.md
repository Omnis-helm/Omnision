# 📘 Omnision Dashboard User Manual & Operational Guidelines

Welcome to the **Omnision Autonomous KPI Storytelling & Causal Governance Dashboard**. This user manual provides step-by-step guidelines for operating the web interface, conducting root-cause investigations, executing manual RCA overrides, and enforcing enterprise governance controls.

---

## 📋 Table of Contents
1. [Launching & Accessing the Dashboard](#1-launching--accessing-the-dashboard)
2. [Authentication & Role Clearances (RBAC)](#2-authentication--role-clearances-rbac)
3. [Sidebar Control Center Navigation](#3-sidebar-control-center-navigation)
4. [Top KPI Metrics Strip](#4-top-kpi-metrics-strip)
5. [Main Investigation Tabs](#5-main-investigation-tabs)
   - [Tab 1: 📊 Executive Narrative](#tab-1--executive-narrative)
   - [Tab 2: 🌳 Causal DAG & Math Proofs](#tab-2--causal-dag--math-proofs)
   - [Tab 3: 🚀 Blue-Sky Challenger & Solutions](#tab-3--blue-sky-challenger--solutions)
   - [Tab 4: 🛠️ Engineer & Ops Playbook](#tab-4--engineer--ops-playbook)
   - [Tab 5: 🔄 Human-in-the-Loop & Continuous Learning](#tab-5--human-in-the-loop--continuous-learning)
6. [Security Boundaries & Graceful Abstention](#6-security-boundaries--graceful-abstention)
7. [Troubleshooting & FAQs](#7-troubleshooting--faqs)

---

## 1. Launching & Accessing the Dashboard

### Terminal Startup Command
Open your terminal in the project root directory and run:

```bash
streamlit run app.py
```

### Access URL
Once started, the application opens automatically in your web browser at:
- **Local URL:** `http://localhost:8501`

---

## 2. Authentication & Role Clearances (RBAC)

Omnision uses strict Role-Based Access Control (RBAC) to enforce enterprise security and prevent data leakage to public cloud LLMs.

![Login Screen](file:///C:/Users/arind/.gemini/antigravity-ide/brain/7721a049-4736-4c72-ab29-c2ac78434587/dashboard_full_view_1788263002830.png)

### Login Credentials Database (`kpi_engine/users.json`)

| Username | Password | Role Clearance | Permissions & Access Scope |
| :--- | :--- | :--- | :--- |
| **`admin`** | `adminpassword` | **`EXECUTIVE_VP`** | **Full Access:** Unlocks Public Cloud LLMs (OpenAI, Anthropic, Gemini), cleared strategic M&A logs, and VP approval controls. |
| **`engineer`** | `engineerpassword` | **`SENIOR_ENGINEER`** | **Technical Access:** Locked to private hosted models (`ollama`, `mock`, `local`), full technical logs & execution playbooks. |
| **`analyst`** | `analystpassword` | **`JUNIOR_ANALYST`** | **Restricted Access:** Locked to private hosted models (`ollama`, `mock`, `local`), redacted executive views. |

> 💡 **Tip:** To add new users or update passwords, edit the `kpi_engine/users.json` file in your repository.

---

## 3. Sidebar Control Center Navigation

The left sidebar serves as the control center for configuring pipeline runs:

### 1. Benchmark Scenario Selector
Select one of 4 pre-configured enterprise scenario benchmarks:
- **Scenario 1:** `1. Stripe v4.1 Gateway Latency Outage (-12.4%)`
- **Scenario 2:** `2. Interacting Price & Volume Drivers (DAG + SHAP)`
- **Scenario 3:** `3. Cold-Start 1-Click Mobile Checkout (<30d)`
- **Scenario 4:** `4. Hybrid Security Matrix (Tier 1 & Tier 2)`

### 2. AI Core Engine Selection
Choose the LLM models for the dual-node swarm:
- **Primary LLM (RCA & Storytelling):** Generates prescriptive RCA and grounded operational solutions.
- **Blue-Sky LLM (Shadow Ideation):** Generates unconstrained alternative proposals for shadow runs.
- *Supported Options:* `openai`, `anthropic`, `gemini`, `ollama`, `mock`, `local`.

> ⚠️ **Data Leak Protection Rule:** If logged in as `SENIOR_ENGINEER` or `JUNIOR_ANALYST`, selecting a public provider (`openai`, `anthropic`, `gemini`) will trigger an RBAC access violation block to prevent PII leakage.

### 3. Bypass Semantic Cache (Force Fresh Inference)
- **Unchecked (Default):** Uses `LLMResponseCache` and pre-calculated model results to deliver instant **< 25ms** response times with 0 token spend.
- **Checked:** Bypasses local caches and re-triggers fresh model inference.

### 4. Fleet Telemetry & Memory Metrics
- **Cumulative Tokens Consumed:** Real-time counter of total LLM tokens spent.
- **Semantic Cached Payloads:** Number of active cached scenario payloads in memory.
- **Active Layer 1 Playbooks:** Number of stored internal runbooks available.

---

## 4. Top KPI Metrics Strip

Upon running a scenario, the top header bar displays immediate diagnostic telemetry:

```
┌─────────────────┬─────────────────┬───────────────────┬───────────────────┬─────────────────────┐
│ ANCHOR METRIC   │ CURRENT VALUE   │ Z-SCORE SHOCK     │ LIFECYCLE STAGE   │ SECURITY APPLIED    │
├─────────────────┼─────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ West Conv Rate  │ 2.80% (-12.50%) │ Z = 5.19 (Severe) │ MATURE            │ PUBLIC_UNRESTRICTED │
└─────────────────┴─────────────────┴───────────────────┴───────────────────┴─────────────────────┘
```

- **Anchor Metric:** The ground-zero KPI isolated by the engine.
- **Current Value:** Latest measured value and percentage variance from baseline mean.
- **Z-Score Shock:** Mathematical standard score ($Z \ge 3.0$ Anomaly, $Z \ge 5.0$ Severe Shock).
- **Lifecycle Stage:** `MATURE` ($30+$ days history) vs `COLD_START` ($< 30$ days history).
- **Security Applied:** Active data classification (e.g., `PUBLIC_UNRESTRICTED`, `TIER_2_TOKEN_MASKING`).

---

## 5. Main Investigation Tabs

The main workspace area is divided into 5 interactive tabs:

---

### Tab 1: 📊 Executive Narrative
*Designed for C-suite executives, VPs, and Product Managers.*

- **Financial Impact ($):** Estimated revenue loss or operational risk exposure.
- **Business Risk Level:** Clear status badge (`HIGH`, `MEDIUM`, or `LOW`).
- **Recommended Action Cards:**
  - **Action Title & Description:** Clear operational solution (e.g., `"Roll back Stripe v4.1 gateway integration"`).
  - **Cost & Impact Estimates:** Estimated cost in USD and expected time-to-impact in minutes.
  - **RACI Owner:** Assigned responsible team (e.g., `Platform Engineering`).
  - **Approval Status Badge:** `AUTO_APPROVED`, `PENDING_VP_APPROVAL`, or `BLOCKED_BY_GUARDRAIL`.

---

### Tab 2: 🌳 Causal DAG & Math Proofs
*Designed for Data Scientists, Analysts, and Incident Leads.*

- **Interactive Directed Acyclic Graph (DAG):** Visualizes causal edges originating from the Anchor Node ($A^*$) out to Tier 1, Tier 2, and Tier 3 dependencies.
- **Composite Causal Weights Table:**
  Displays the mathematical proof for candidate ranking:
  $$\text{Composite Weight } W = \text{Contextual Relevance } (CR) \times \text{Causal Impact } (CI)$$
- **SHAP Attribution Chart:** Displays relative variance percentages for ambient variables (e.g. competitor promotions, weather spikes) derived from the trained **XGBoost Regressor**.
- **Discarded Noise Candidates:** Lists candidate logs that were pruned by "The Cage" or "The Brakes" as noise.

---

### Tab 3: 🚀 Blue-Sky Challenger & Solutions
*Designed for Architecture & Strategy teams.*

- **Unconstrained Shadow Run Proposals:** Displays creative, alternative mitigation ideas generated by the Blue-Sky Challenger persona (e.g., `"Migrate checkout cluster to alternate cloud provider"`).
- **Comparative Risk & Cost Matrix:** Contrasts grounded runbook solutions with high-impact challenger ideas.

---

### Tab 4: 🛠️ Engineer & Ops Playbook
*Designed for DevOps, SREs, and On-Call Engineers.*

- **Technical Root Cause:** Exact log text and component ID causing the anomaly.
- **System Logs Stream:** Raw telemetry log entries.
- **Terminal Execution Playbook:**
  - **Target Environment:** `production-cluster`, `prod-traffic-mesh`, etc.
  - **Execution Command:** Copy-paste terminal command ready for immediate execution:
    ```bash
    helm rollback stripe-gateway 4.0 && traffic-router set --split stripe:85,adyen:15
    ```

---

### Tab 5: 🔄 Human-in-the-Loop & Continuous Learning
*Designed for Analysts overriding AI decisions and training the continuous learning loop.*

#### 1. Human RCA Override Panel
If the AI selects a secondary or incorrect root cause:
1. Select the **Demoted Driver** from the dropdown.
2. Select a **Promoted Driver** or check **Inject Custom Root Cause**.
3. Type custom explanatory text (e.g., `"Critical database deadlocks on postgres checkout_sessions table"`).
4. Click **Apply RCA Override & Recalibrate**.
5. *Result:* The engine recalibrates its semantic threshold ($\eta = 0.05$), demotes the false driver, and regenerates governed playbooks.

#### 2. Reject Recommended Fix Panel
If a proposed fix cannot be executed due to operational constraints:
1. Type your feedback (e.g., `"Cannot scale deployment due to regional cloud quota limits"`).
2. Click **Reject Recommended Fix & Re-synthesize**.
3. *Result:* The engine appends the rejection feedback to context and dispatches the swarm to generate an alternative solution.

---

## 6. Security Boundaries & Graceful Abstention

When a user logged in as `SENIOR_ENGINEER` or `JUNIOR_ANALYST` selects **Scenario 4 (Security Clearance Matrix)**:

1. **Security Policy Enforcement:**
   The primary root cause relates to a **Tier 1 Strategic Domain** (e.g., unannounced M&A advisor fees).
2. **Graceful Abstention Screen:**
   Rather than hallucinating false secondary reasons or leaking confidential data, Omnision displays a **Graceful Abstention** notice:
   
   > 🛡️ **Omnision Security Boundary: Graceful Abstention Enforced**
   > *Primary causal driver pruned under Tier 1 Strategic Security Policy.*

3. **Elevate Clearance Button:**
   Users with proper authorization can click **"🔓 Elevate Clearance to EXECUTIVE_VP"** to switch roles and unlock the complete investigation.

---

## 7. Troubleshooting & FAQs

### Q1: The browser shows a blank dark screen when opening `http://localhost:8501`.
- **Cause:** No LLM provider was selected in the sidebar, or Streamlit halted execution.
- **Solution:** Select `"gemini"` or `"mock"` in the **Primary LLM** and **Blue-Sky LLM** sidebar dropdowns, or refresh the page.

### Q2: How do I enable real Google Gemini or OpenAI API calls?
1. Open your `.env` file in the project root.
2. Set your keys:
   ```ini
   GOOGLE_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```
3. Ensure you are logged in as `admin` (`EXECUTIVE_VP` tier).
4. Select `"gemini"` or `"openai"` in the sidebar dropdowns.

### Q3: How do I clear cached responses and force fresh ML/LLM inference?
Check the **"Bypass Semantic Cache (Force Fresh Inference)"** checkbox in the left sidebar.

### Q4: How do I run the automated test suite?
Run the following command in your terminal:
```bash
python -m pytest tests/
```
All 12 test cases will execute and verify causal scoring, security pruning, and closed-loop learning.
