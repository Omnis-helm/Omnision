# ⚡ Omnision: Autonomous KPI Storytelling & Causal Governance Engine

![Version](https://img.shields.io/badge/version-3.1-blue.svg)
![Status](https://img.shields.io/badge/status-Proof%20of%20Concept-orange.svg)
![Architecture](https://img.shields.io/badge/Architecture-Neuro--Symbolic-purple.svg)
![ML Engine](https://img.shields.io/badge/ML%20Engine-XGBoost%20%2B%20Exact%20Shapley-green.svg)

**Omnision** takes a business KPI anomaly from **detection** to **causal diagnosis**, a written **story** of what
happened, **governed fixes**, and **closed-loop learning** from the humans who review it.

> 📘 Dashboard operating guide: [manual.md](manual.md)

---

## 📋 Contents
1. [Principles](#-principles)
2. [Technology stack](#-technology-stack)
3. [Pipeline (Stages 0–7)](#-pipeline-stages-07)
4. [Scenario walkthroughs](#-scenario-walkthroughs)
5. [Security & RBAC](#-security--rbac)
6. [Configuration](#-configuration)
7. [Install & run](#-install--run)
8. [Tests](#-tests)
9. [Repository map](#-repository-map)
10. [Taking it to production](#-taking-it-to-production)

---

## 🧠 Principles

**Neuro-symbolic bounding ("caging the LLM").**
- *Symbolic layer:* Z-scores, EWMA, metric-tree algebra, confidence bands, a bounded causal DAG and exact Shapley
  values decide **which evidence is causal** and **which fixes are allowed**.
- *Neural layer:* an LLM (optional) writes the narrative and may propose extra fixes, but only from the scored
  evidence, and every proposal still passes the deterministic Critic and the Supervisor.
- **Fail closed:** if an LLM is unreachable, mis-configured or returns junk, Omnision falls back to its grounded
  playbook network and local semantic checks, and reports the fallback. An error is never an approval.

```
 Stage 0  Ingest 4 sources (hourly web, 15-min IT, daily sales, weekly market) → reconcile → train global model
 Stage 1  Detect: Z-score | dual-window drift | cold-start tripwire (EWMA + surrogate)      → Anchor A*
 Stage 2  Directional scoping (upstream / downstream) + Hybrid Security Matrix               → abstain if needed
 Stage 3  The Cage: time window + region/platform + Graph-RAG memory (similarity-thresholded)
 Stage 4  Score W = CR × CI   (metric-tree math, DiD, CI bands, SHAP on the global model)
 Stage 3b The Brakes: W ≥ 0.40, ≤ 2 hops, 0.85 attenuation per extra hop                     → causal DAG
 Stage 5  Dual-channel suggestions: Layer 1 playbooks, Layer 3 levers, Layer 2 precedents (+ LLM) | Blue-Sky
 Stage 6  LangGraph swarm: Critic → Supervisor → (reject → regenerate, max 3) → governed payload + narrative
 Stage 7  Learning: RCA overrides, noise flags, rejected fixes, trust weights, new playbooks → cache invalidation
```

---

## 🛠️ Technology stack

| Area | Used for |
|---|---|
| Streamlit, Plotly | Executive dashboard (5 tabs) |
| FastAPI | Token-authenticated REST API |
| XGBoost (scikit-learn fallback), pandas, NumPy | Global revenue model + exact interventional Shapley values |
| NetworkX | Bounded acyclic causal graph |
| LangGraph (sequential fallback) | Primary swarm loop + parallel Blue-Sky branch |
| LangChain OpenAI / Anthropic / Google GenAI / Ollama, direct REST fallbacks | Optional LLM narrative, proposals and review |
| TF-IDF vector store (FAISS + MiniLM optional) | Institutional memory of incidents and noise signatures |
| Pydantic v2 | Data contracts and the Unified Master Payload |

---

## ⚙️ Pipeline (Stages 0–7)

### Stage 0 — Ingestion & reconciliation (`data/generator.py`, `data/reconciler.py`)
Four synthetic sources (hourly web analytics, 15-minute IT latency, daily sales, weekly market snapshots) are
resampled into one daily table. A global model (`ml/global_model.py`) learns **West daily net revenue** from
ambient drivers only (marketing spend, competitor price, weather severity, server latency). Columns derived from
revenue (traffic, AOV, cart abandonment) are excluded to avoid target leakage. The anomaly day is held out of
training and explained with exact Shapley values (`ml/shap_explainer.py`). The model is cached in memory and on
disk with a schema signature, so a stale pickle is ignored and retrained.

### Stage 1 — Detection (`detector/`)
Each scenario ships raw telemetry (30 days for mature KPIs, 6 days for the cold-start KPI). The detector computes
the anchor itself:
- **Mature:** |Z| ≥ 3.0 on the trailing 30 days (≥ 5.0 is a severe shock), else a 7-day vs 28-day EWMA drift ≥ 5%.
- **Cold start (< 30 samples):** EWMA (α = 0.3) baseline × the seasonality of a mature surrogate KPI, 5% tripwire.
  Graduates to Z-scores at 30 samples.

`engine.scan_fleet()` runs the same detector across all live KPI series.

### Stage 2 — Scoping & security (`scoper/`)
- **Directional scoping** picks upstream / downstream / midstream from the variance decomposition and drops
  evidence tagged with the opposite side of the value chain.
- **Hybrid Security Matrix**
  - *Tier 1 pruning:* strategic secrets are removed for users without clearance; if the removed node was a major
    driver the engine **abstains** and returns a SHA-256 audit receipt instead of an incomplete story.
  - *Tier 2 masking:* dollar values / PII are masked for users below clearance, and **always** masked before evidence
    is sent to a public cloud LLM, even for a VP.

### Stage 3 — Bounded graph (`graph/bounded_builder.py`)
- **The Cage:** evidence must fall in `[-48h, +12h]` (30 days for drift anomalies) and match region/platform.
  Institutional memory is queried with the anchor and the caged evidence; only hits with similarity ≥ 0.30 are
  attached, as **context** (never as a root cause).
- **The Brakes:** edges with W < 0.40 are severed. A node that acts through another node (`metadata.causes`)
  becomes a hop-2 edge (e.g. competitor sale → volume contraction → revenue); paths are capped at 2 hops and
  attenuated by 0.85 per extra hop.

### Stage 4 — Composite causal scoring (`causal/`)
`W = CR × CI`
- `CR = 0.35·Wt + 0.35·We + 0.30·Ws` — temporal decay, shared dimension tags, semantic similarity (below the
  human-tunable semantic threshold, Ws counts as 0).
- `CI = 0.4·Wsnr + 0.6·Wcf`, where `Wcf` comes from the strongest available evidence tier:
  - Tier 1 Gold: measured contribution, price × volume metric tree `ΔR = PΔV + VΔP + ΔPΔV`, or share of the anchor's
    delta in its own units (e.g. margin points)
  - Tier 2 Silver: difference-in-differences against a control cohort
  - Tier 3 Bronze: SHAP share from the global model (ambient drivers, sign-checked), or half the CI-band shock
    weight when a node's impact is unquantified
  - A proven zero contribution collapses CI to 0. Nodes a human demoted are penalised ×0.5.

### Stage 5 — Dual-channel suggestion network (`suggester/`)
- **Channel A (grounded):** every surviving driver is matched against Layer 1 playbooks, Layer 3 lever-backed
  actions and Layer 2 market precedents. Confidence = agent trust weight × match strength × driver rank.
  With a real LLM selected, the model also proposes up to 3 fixes and writes the narrative, from the same evidence.
- **Channel B (Blue-Sky):** one unconstrained strategic idea, critiqued by the Reality Checker, never auto-approved.

### Stage 6 — Governance swarm (`governor/langgraph_orchestrator.py`)
`rca_agent → deterministic_validator (Critic) → llm_supervisor`, looping back to `rca_agent` with feedback when
everything is rejected (max 3 iterations, then a manual-triage circuit breaker). In parallel:
`blue_sky_agent → blue_sky_critic`. The Critic checks forbidden commands, lever availability, alignment with the
causal chain, liveness, a 24h impact window and RACI cost tiers (≤ $10k auto, ≤ $100k director, above that VP).
**Only approved proposals reach the executive view;** everything else is listed with its rejection reason.

### Stage 7 — Closed-loop learning (`learning/`, `pipeline.py`)
| Human action | Effect on later runs |
|---|---|
| Override root cause (promote evidence / inject text) | Human-verified driver is used until reset; demoted node penalised; semantic threshold lowered by η = 0.05 |
| Flag as noise | Signature added to memory; matching alerts for that KPI are suppressed |
| Deny a fix | Fix is excluded for that KPI; producing agent's trust × (1 − 0.15) |
| Approve a fix | Producing agent's trust × (1 + 0.10) |
| Modify & approve | New Layer 1 playbook (trigger derived from the root cause) is proposed next time |

Every learning event bumps a version and invalidates the semantic cache for the KPI.

---

## 🔬 Scenario walkthroughs (mock provider, deterministic)

| | Scenario 1 — Stripe outage | Scenario 2 — Price × volume | Scenario 3 — Cold start | Scenario 4 — Security matrix (VP) |
|---|---|---|---|---|
| Detection | Z = 5.19 (severe) | Z = 4.07 | tripwire: −5.8% vs EWMA×surrogate baseline 3.93 | Z = 7.17 |
| Primary driver | Stripe v4.1 timeout (W 0.68) | Price discount (W 0.50) | Biometric SDK failure (W 0.47) | M&A advisor fee (W 0.65, 74% of the margin drop) |
| Other evidence | Support tickets corroborate (hop 2) | Volume contraction (W 0.45) ← competitor flash sale (hop 2, SHAP ≈ −71%) | — | SLA penalty (W 0.42, 26%) |
| Ruled out | Email campaign (0 contribution), East warehouse (out of scope) | Heatwave (W 0.29, SHAP ≈ −18%) | — | Tariff surcharge (W 0.34) |
| Memory | HIST-001 (similar Stripe incident) | HIST-004 | HIST-005 | HIST-006 |
| Top fix | Roll back Stripe v4.1 → v4.0 ($0, auto) | Cap discount at 3% + price-match top 5 SKUs ($6.8k, auto) | Disable biometric step via feature flag + SDK hotfix ($0, auto) | Reclassify fee as non-recurring vs corporate reserve ($0, auto) |
| Also approved | Shift 15% traffic to Adyen; Envoy circuit breaker | Loyalty bundle ($15k, director) | — | 3PL SLA penalty recovery |
| Blue-Sky | Multi-cloud checkout ($125k, needs procurement) | Price-intelligence membership tier | Passkeys | Earn-out renegotiation |

Engineers and analysts get **ABSTAINED** on Scenario 4 because the primary driver is a Tier 1 secret.
SHAP percentages are from the scikit-learn fallback; XGBoost gives similar but not identical values.

---

## 🔒 Security & RBAC

| Role | Executive view | Override RCA / deny fixes | Approve ≤ $100k | Approve > $100k / promote Blue-Sky | Public LLMs | Tier 1 secrets |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `EXECUTIVE_VP` | ✅ | ✅ | ✅ | ✅ | ✅ (Tier 2 masked) | ✅ |
| `SENIOR_ENGINEER` | ✅ | ✅ | ✅ | ❌ | ❌ | 🔒 abstain |
| `JUNIOR_ANALYST` | ✅ (Tier 2 masked) | ❌ | ❌ | ❌ | ❌ | 🔒 abstain |

- Enforced in the **backend** (`auth.assert_providers_allowed` inside `run_pipeline`, API token roles), not only the UI.
- Passwords: salted PBKDF2-SHA256 in `kpi_engine/users.json`. **Change the demo passwords** with
  `python -m kpi_engine.auth set-password <user> <ROLE>`.
- Demo accounts: `admin / adminpassword` (VP), `engineer / engineerpassword`, `analyst / analystpassword`.

---

## 🛠️ Configuration
Copy `.env.example` to `.env`. Key settings:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `mock` | Default provider in the UI (`mock`, `ollama`, `openai`, `anthropic`, `gemini`) |
| `OPENAI_MODEL` / `ANTHROPIC_MODEL` / `GEMINI_MODEL` | `gpt-4o` / `claude-sonnet-4-5` / `gemini-2.5-flash` | Model names, change to what your account offers |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `http://localhost:11434`, `llama3` | Private local model |
| `PREFER_LOCAL_TOOLS` | `True` | TF-IDF memory; `False` = FAISS + embeddings |
| `ENABLE_DENSE_EMBEDDINGS` | `False` | MiniLM semantic similarity instead of lexical |
| `ENABLE_WEB_INTELLIGENCE` | `False` | yfinance + FinBERT corroboration of external evidence |
| `OMNISION_API_SECRET` | random | Signing key for API tokens |

Engine thresholds live in `kpi_engine/config.py` (`SystemConfig`).

---

## 🚀 Install & run
```bash
pip install -r requirements.txt
streamlit run app.py                         # dashboard → http://localhost:8501
uvicorn kpi_engine.api.app:app --reload      # REST API → http://localhost:8000/docs
```
API flow: `POST /api/login` → bearer token → `POST /api/investigate`, `/api/override-rca`, `/api/reject-fix`,
`/api/approve-fix`, `GET /api/telemetry`, `/api/fleet-scan`.

---

## 🧪 Tests
```bash
python -m pytest tests/
```
34 tests across 8 files: causal math & SHAP (no leakage, competitor dominates, Shapley efficiency), detection
(cold start, graduation, drift, fleet scan), Critic & grounded matching, governance loop (garbage / destructive
LLM output rejected, circuit breaker, LLM outage falls back), security (pruning, masking, outbound masking,
backend provider policy, abstention receipt), auth, closed-loop learning, and end-to-end expectations for all four
scenarios.

---

## 📂 Repository map
```
Omnision/
├── app.py                       # streamlit run app.py
├── requirements.txt / .env.example
├── tests/                       # pytest suite (34 tests)
└── kpi_engine/
    ├── config.py                # SystemConfig + .env loader
    ├── auth.py                  # PBKDF2 users, API tokens, provider policy
    ├── pipeline.py              # KPIStorytellingEngine: Stages 0-7 + learning handlers
    ├── data/                    # models, generator, reconciler, seed scenarios (with raw telemetry)
    ├── detector/                # Z-score / drift detector, cold-start phased handover
    ├── scoper/                  # directional router, Hybrid Security Matrix
    ├── graph/                   # The Cage & The Brakes, NetworkX DAG model
    ├── causal/                  # contextual relevance, counterfactual tiers, Shapley, composite scorer
    ├── ml/                      # global model, exact SHAP explainer, local text/vector tools, caches
    ├── memory/                  # institutional memory vector store
    ├── suggester/               # layers store, dual-channel suggester, LLM prompts & narrative
    ├── governor/                # LangGraph orchestrator, Critic, Supervisor, actor swarm, LLM factory, schemas
    ├── learning/                # RCA corrections, trust tuning, dynamic playbooks
    ├── api/app.py               # FastAPI
    └── ui/streamlit_app.py      # dashboard
```

---

## 🏢 Taking it to production
Omnision is **advisory**: an approval is a governance stamp handed to the RACI owner, never an automatic execution.
To go beyond the POC:
1. **Data:** replace `seed_scenarios.py` with webhooks from Datadog / Prometheus / CloudWatch and evidence from
   logs, tickets and change feeds; replace the synthetic generator with your warehouse.
2. **Memory:** point the vector store at post-mortems, Confluence and Jira (`PREFER_LOCAL_TOOLS=False`).
3. **Playbooks & levers:** load Layers 1–3 from your runbook system and service catalog instead of `layers_data.py`;
   persist learning state (overrides, trust weights, playbooks), which is in memory today.
4. **Hand-off:** send approved actions to PagerDuty / Slack / Jira / ServiceNow.
5. **Identity & audit:** replace `users.json` with SSO, and log payloads and approvals to a database.
