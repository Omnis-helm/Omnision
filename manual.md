# 📘 Omnision Dashboard Manual

How to run investigations, read the causal story, govern fixes and teach the engine.

---

## 1. Launch
```bash
streamlit run app.py
```
Opens at `http://localhost:8501`. The first start trains the global model (a few seconds); later starts load it from
`kpi_engine/ml/saved_global_model.pkl`.

## 2. Log in

| Username | Password | Role | Can do |
|---|---|---|---|
| `admin` | `adminpassword` | `EXECUTIVE_VP` | Everything: public cloud LLMs, Tier 1 secrets, approve any spend, promote Blue-Sky ideas |
| `engineer` | `engineerpassword` | `SENIOR_ENGINEER` | Private LLMs only, override root causes, approve/deny fixes up to $100k |
| `analyst` | `analystpassword` | `JUNIOR_ANALYST` | Private LLMs only, read-only; Tier 2 values masked |

Change these before sharing the app: `python -m kpi_engine.auth set-password <user> <ROLE>`.

## 3. Sidebar
- **Benchmark scenario:** the four reference incidents.
- **Primary / Blue-Sky LLM:** only providers your role may use are listed. `mock` runs fully offline using the
  grounded playbook network and a template narrative; `ollama` calls your local model; `openai` / `anthropic` /
  `gemini` need a key in `.env`. A missing key or an outage shows a warning, and the engine falls back to grounded
  playbooks instead of failing. With a public provider, Tier 2 evidence is masked before it leaves.
- **Bypass semantic cache:** recompute instead of serving the cached payload (cached runs cost 0 tokens).
- **Reset human overrides for this scenario:** clears verified drivers, demotions and denied fixes for the KPI.
- **Fleet telemetry:** cumulative tokens and cost, cached payloads, Layer 1 playbook count, live fleet scan.

## 4. Header metrics
Anchor KPI · current value and % change · Z-score (or the trigger rule) · lifecycle stage (`MATURE` /
`COLD_START`) · security applied (`PUBLIC_UNRESTRICTED`, `TIER_2_TOKEN_MASKING`, or Tier 1 pruning).

## 5. Tabs

### Tab 1 · Executive narrative
- Financial exposure, business risk, primary causal weight and its confidence (`HIGH`, `LOW`, `HUMAN_VERIFIED`).
- **The story:** what moved, by how much, the causal chain, what memory recalls and what was ruled out. Its source
  (LLM or deterministic template) is shown under it, with the governance status.
- **Root cause:** confirm it, or open *Override root cause*:
  - *Promote other evidence* – pick another node;
  - *Inject verified root cause* – type what really happened;
  - *Flag as noise* – teaches memory that this pattern is a false alarm (later alerts are suppressed).
- **Governed mitigation actions:** only fixes approved by the Critic **and** the Supervisor. Each card shows cost,
  time to impact, expected recovery, RACI owner, approval tier and both verdicts.
  - *Approve* – raises the trust weight of the agent that proposed it. VP-tier spend needs `EXECUTIVE_VP`.
  - *Deny* – removes the fix for this KPI, lowers that agent's trust, and regenerates alternatives.
  - *Modify & approve* – records what you actually ran; it becomes a new Layer 1 playbook.

### Tab 2 · Causal DAG & math
- Graph: red anchor, green hop-1 drivers, purple hop-2 drivers or corroboration, grey dotted memory, yellow masked.
- Scoring table: Wt, We, Ws → CR; Wcf → CI; W = CR × CI; evidence tier; surviving vs discarded.
- Scenario 2 adds the price × volume metric tree and the SHAP bar chart from the global model.
- Expanders: Stage 1 detection report, what the Cage pruned or scoped out, every discarded candidate with its reason.

### Tab 3 · Blue-sky challenger
One unconstrained idea with a Reality Checker critique. It is never auto-approved; a VP can *Promote to main*, which
adds it to Tab 1 as `PROMOTED_FROM_SANDBOX` (requires a shadow run).

### Tab 4 · Engineer & ops playbook
Technical root cause, evidence log stream, the execution command for the top approved fix (plus alternatives) and
the ops view (bottleneck, SLA impact, owners). Commands are handed to the owner; Omnision never executes them.

### Tab 5 · Telemetry & learning
Latency, input/output tokens, cost, cache status, LLM fallbacks, agent trust weights with the feedback log, the
current semantic threshold, human overrides and denied fixes, the Layer 1 playbook library and the raw payload JSON.

## 6. Graceful abstention
`SENIOR_ENGINEER` and `JUNIOR_ANALYST` opening Scenario 4 see **Graceful abstention enforced**: the main driver is a
Tier 1 secret (unannounced M&A), so the engine refuses to tell a partial story. An audit receipt (SHA-256) is shown.
Sign in as an `EXECUTIVE_VP` to see the full investigation.

## 7. FAQ
- **Why does a run say "Served from the semantic cache"?** Same scenario, role, providers and learning state as a
  previous run. Tick *Bypass semantic cache* to recompute.
- **The LLM output looks generic.** Check Tab 5 for fallbacks: a missing key or an unreachable model makes the
  engine use grounded playbooks and the template narrative.
- **Run the tests:** `python -m pytest tests/` (34 tests).
