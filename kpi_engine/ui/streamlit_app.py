"""
Omnision: Autonomous KPI Storytelling & Causal Governance Engine
Interactive Executive Dashboard (Streamlit)

Run:  streamlit run app.py          (or)  streamlit run kpi_engine/ui/streamlit_app.py
"""

import sys
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from kpi_engine.config import CONFIG, PUBLIC_LLM_PROVIDERS
from kpi_engine.auth import authenticate, provider_allowed
from kpi_engine.data.models import UserClearance
from kpi_engine.governor.llm_factory import get_llm, MissingAPIKeyError
from kpi_engine.pipeline import KPIStorytellingEngine, SCENARIOS
from kpi_engine.scoper.security_matrix import clearance_level

st.set_page_config(
    page_title="Omnision — KPI Storytelling Engine",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Starting Omnision engine (training global model)...")
def get_engine() -> KPIStorytellingEngine:
    """One engine per server process: learning (overrides, trust, playbooks) is shared institutional memory."""
    return KPIStorytellingEngine()


engine = get_engine()

SCENARIO_LABELS = {
    "SCENARIO_1_STRIPE_GATEWAY_OUTAGE": "1. Stripe v4.1 gateway latency outage (-12.5%)",
    "SCENARIO_2_MULTIVARIATE_DAG_SHAP": "2. Interacting price & volume drivers (DAG + SHAP)",
    "SCENARIO_3_COLD_START_PHASED_HANDOVER": "3. Cold-start 1-click mobile checkout (<30d)",
    "SCENARIO_4_SECURITY_CLEARANCE_MATRIX": "4. Hybrid security matrix (Tier 1 & Tier 2)",
}
ALL_PROVIDERS = ["mock", "ollama", "openai", "anthropic", "gemini"]

# ============================================================================ authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.active_role = UserClearance.PUBLIC.value

if not st.session_state.logged_in:
    st.title(":material/lock: Omnision secure login")
    st.caption("Sign in to access the autonomous governance engine.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            role = authenticate(username, password)
            if role is not None:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.active_role = role.value
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

active_role = UserClearance(st.session_state.active_role)
is_vp = clearance_level(active_role) >= clearance_level(UserClearance.EXECUTIVE_VP)
is_engineer = clearance_level(active_role) >= clearance_level(UserClearance.SENIOR_ENGINEER)

# ============================================================================ sidebar
st.sidebar.markdown("## :material/bolt: Omnision control center")
st.sidebar.markdown(f":material/person: **{st.session_state.username}** · `{active_role.value}`")
if st.sidebar.button("Log out"):
    for k in ("logged_in", "username", "active_role", "promoted"):
        st.session_state.pop(k, None)
    st.rerun()
st.sidebar.divider()

selected_scenario_id = st.sidebar.selectbox(
    "Benchmark scenario", options=list(SCENARIOS), format_func=lambda x: SCENARIO_LABELS.get(x, x))

st.sidebar.markdown("### :material/settings: AI core engine")
allowed_providers = [p for p in ALL_PROVIDERS if provider_allowed(active_role, p)]
if len(allowed_providers) < len(ALL_PROVIDERS):
    st.sidebar.caption("Public cloud LLMs (OpenAI, Anthropic, Gemini) require `EXECUTIVE_VP` clearance.")
default_provider = CONFIG.llm_provider if CONFIG.llm_provider in allowed_providers else "mock"
primary_llm = st.sidebar.selectbox("Primary LLM (RCA & storytelling)", allowed_providers,
                                   index=allowed_providers.index(default_provider))
bluesky_llm = st.sidebar.selectbox("Blue-sky LLM (shadow ideation)", allowed_providers,
                                   index=allowed_providers.index(default_provider))
for prov in {primary_llm, bluesky_llm}:
    if prov in PUBLIC_LLM_PROVIDERS:
        try:
            get_llm(prov)
        except MissingAPIKeyError as e:
            st.sidebar.warning(f"{prov}: {e} The swarm will fall back to grounded playbooks.")
        except Exception as e:
            st.sidebar.warning(f"{prov}: {e}")
    if prov in PUBLIC_LLM_PROVIDERS:
        st.sidebar.caption(f":material/shield: Tier-2 evidence is masked before it is sent to {prov}.")

force_refresh = st.sidebar.checkbox("Bypass semantic cache (force fresh inference)", value=False)
if st.sidebar.button("Reset human overrides for this scenario"):
    engine.reset_learning(selected_scenario_id)
    st.sidebar.success("Overrides, demotions and rejected fixes cleared for this KPI.")

st.sidebar.divider()
st.sidebar.markdown("### :material/monitoring: Fleet telemetry & memory")
st.sidebar.metric("Cumulative LLM tokens", f"{engine.supervisor.cumulative_token_spend:,}")
st.sidebar.metric("Cumulative LLM cost", f"${engine.supervisor.cumulative_cost_usd:,.4f}")
st.sidebar.metric("Cached payloads", f"{len(engine.supervisor.semantic_cache)}")
st.sidebar.metric("Layer 1 playbooks", f"{len(engine.layers_store.layer_1_playbooks)}")
fleet = engine.scan_fleet()
st.sidebar.caption(f"Live fleet scan ({len(engine.contracts)} KPIs): " +
                   (", ".join(f"{a.kpi_id} (Z={a.z_score})" for a in fleet) if fleet else "all KPIs within bounds."))

# ============================================================================ run
st.title("Omnision")
st.caption("Autonomous root-cause diagnosis · multivariate causal inference · multi-agent governance · continuous learning")

try:
    result = engine.run_pipeline(scenario_id=selected_scenario_id, user_role=active_role, force_refresh=force_refresh,
                                 primary_llm=primary_llm, bluesky_llm=bluesky_llm)
except PermissionError as e:
    st.error(f":material/block: {e}")
    st.stop()
except Exception as e:
    st.error(f":material/error: Execution error: {e}")
    st.stop()

if result.get("status") == "NO_ANOMALY":
    st.info(f":material/check_circle: {result['reason']}")
    st.json(result.get("detection", {}))
    st.stop()

if result.get("status") == "ABSTAINED":
    st.error(":material/shield: **Omnision security boundary: graceful abstention enforced**")
    col_s1, col_s2 = st.columns([3, 2])
    with col_s1:
        st.markdown(f"### {result.get('reason')}")
        st.markdown(
            "**Why this happened (Hybrid Security Matrix):**\n"
            "* The primary root cause of this anomaly is classified under **Tier 1 strategic domain pruning** "
            "(e.g. unannounced M&A, HR terminations).\n"
            f"* Your role (`{active_role.value}`) lacks `EXECUTIVE_VP` clearance.\n"
            "* Rather than presenting an incomplete or hallucinated story, the engine **abstains**.\n\n"
            "To view the full investigation, log out and sign in with an `EXECUTIVE_VP` account.")
    with col_s2:
        st.markdown("### :material/receipt_long: Security audit receipt")
        st.json(result.get("security_audit", {}))
    st.stop()

# ============================================================================ success
anchor = result["anchor"]
master = result["master_payload"]
dag_payload = result["dag_payload"]
scored_nodes = result["scored_nodes"]
surviving_nodes = result["surviving_evidence"]
discarded_noise = result["discarded_noise"]
primary_driver = result.get("primary_driver")
ctx = result.get("context", {})
raw_state = result.get("raw_state", {})
threshold = CONFIG.edge_prune_weight_threshold

if result.get("cache_hit"):
    st.caption(":material/bolt: Served from the semantic cache (0 tokens). Tick *Bypass semantic cache* to recompute.")
if master.runtime_metadata.llm_errors:
    with st.expander(f":material/warning: {len(master.runtime_metadata.llm_errors)} LLM fallback(s) occurred"):
        for err in master.runtime_metadata.llm_errors:
            st.write(f"- {err}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Anchor metric", anchor.kpi_id)
c2.metric("Current value", f"{anchor.current_value:,.2f}", f"{anchor.variance_pct:+.2f}%")
c3.metric("Z-score", f"{anchor.z_score:.2f}",
          "Severe shock" if anchor.z_score >= CONFIG.z_score_shock_threshold else anchor.trigger_rule.replace("_", " ").title())
c4.metric("Lifecycle stage", anchor.lifecycle_stage.value)
c5.metric("Security applied", master.anchor_reference.security_applied)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    ":material/menu_book: Executive narrative",
    ":material/account_tree: Causal DAG & math",
    ":material/rocket_launch: Blue-sky challenger",
    ":material/terminal: Engineer & ops playbook",
    ":material/insights: Telemetry & learning",
])

# ============================================================================ TAB 1
with tab1:
    m1, m2, m3 = st.columns(3)
    m1.metric("Financial exposure", f"${master.executive_view.financial_impact_usd:,.0f}")
    m2.metric("Business risk", master.executive_view.business_risk_level)
    m3.metric("Primary causal weight", f"{master.anchor_reference.causal_weight:.2f}",
              master.anchor_reference.confidence.replace("_", " ").title())

    st.markdown("### :material/auto_stories: The story")
    st.markdown(master.executive_view.narrative or "_No narrative generated._")
    st.caption(f"Narrative source: {master.executive_view.narrative_source} · Governance: {master.supervisor_status}")
    st.divider()

    rca_col, fix_col = st.columns(2)
    with rca_col:
        st.markdown("### :material/search: Root cause")
        st.info(f"**{master.anchor_reference.primary_driver}**\n\n"
                f"Node `{master.anchor_reference.primary_driver_id}` · W = {master.anchor_reference.causal_weight:.2f} "
                f"· confidence {master.anchor_reference.confidence}")
        if result.get("noise_verdict"):
            st.warning(f"Matched noise signature `{result['noise_verdict']['historical_id']}` "
                       f"(similarity {result['noise_verdict']['similarity']:.2f}).")

        if is_engineer:
            if st.button(":material/check_circle: Confirm root cause", key="approve_rca"):
                st.success("Root cause confirmed.")
            with st.expander(":material/edit: Override root cause (human-in-the-loop)"):
                candidates = {n.node_id: n.title for n in surviving_nodes + discarded_noise
                              if primary_driver is None or n.node_id != primary_driver.node_id}
                mode = st.radio("Correction", ["Promote other evidence", "Inject verified root cause", "Flag as noise"],
                                horizontal=True, key="rca_mode")
                promoted_id, injected = None, None
                if mode == "Promote other evidence":
                    if candidates:
                        promoted_id = st.selectbox("Evidence to promote", list(candidates),
                                                   format_func=lambda k: f"{k} — {candidates[k]}")
                    else:
                        st.caption("No alternative evidence nodes available.")
                else:
                    injected = st.text_input("Explanation", placeholder="e.g. Postgres deadlocks on checkout_sessions",
                                             key="rca_text")
                if st.button("Apply override & regenerate", key="apply_override"):
                    if mode == "Promote other evidence" and not promoted_id:
                        st.error("Select a node to promote.")
                    elif mode == "Inject verified root cause" and not injected:
                        st.error("Enter the verified root cause.")
                    else:
                        res = engine.handle_human_rca_override(
                            scenario_id=selected_scenario_id,
                            demoted_node_id=primary_driver.node_id if primary_driver is not None else None,
                            promoted_node_id=promoted_id, custom_injected_text=injected,
                            user_role=active_role, primary_llm=primary_llm, bluesky_llm=bluesky_llm,
                            is_noise=(mode == "Flag as noise"), analyst_id=st.session_state.username)
                        st.success(f"{res['status'].replace('_', ' ').title()}.")
                        st.rerun()
        else:
            st.caption("Root-cause overrides require `SENIOR_ENGINEER` clearance.")

    with fix_col:
        st.markdown("### :material/build: Governed mitigation actions")
        actions = master.executive_view.recommended_actions
        promoted = st.session_state.get("promoted", {}).get(selected_scenario_id, [])
        if not actions:
            st.info("No recommended actions.")
        for i, action in enumerate(actions + promoted):
            box = st.container(border=True)
            box.markdown(f"**{action.action}**")
            box.caption(f"`{action.action_id}` · {action.source_layer} · owner: {action.raci_owner}")
            box.markdown(
                f"- Status: `{action.approval_status}` · confidence {action.model_confidence_weight or 0:.2f}\n"
                f"- Cost `${action.estimated_cost_usd:,.0f}` · time to impact `{action.time_to_impact_minutes} min`\n"
                f"- Expected recovery: {action.expected_damage_reverted or 'Unknown'}\n"
                f"- Critic: {action.critic_verdict or '-'}\n"
                f"- Supervisor: {action.supervisor_verdict or '-'}")
            needs_vp = action.approval_status in ("PENDING_VP_APPROVAL", "PROMOTED_FROM_SANDBOX")
            can_approve = is_vp or (is_engineer and not needs_vp)
            b1, b2 = box.columns(2)
            if b1.button(":material/check_circle: Approve", key=f"approve_fix_{i}", disabled=not can_approve):
                engine.handle_accepted_fix(selected_scenario_id, action.action_id, action.source_layer or "",
                                           action.action, user_id=st.session_state.username)
                st.success("Approved - trust weight of the producing agent increased. Hand off to the RACI owner.")
            if b2.button(":material/cancel: Deny", key=f"deny_fix_{i}", disabled=not is_engineer):
                engine.handle_rejected_fix(selected_scenario_id, primary_driver, action.action, active_role,
                                           primary_llm, bluesky_llm, action_id=action.action_id,
                                           source_layer=action.source_layer, user_id=st.session_state.username)
                st.rerun()
            if is_engineer:
                with box.expander("Modify & approve (teaches a new Layer 1 playbook)"):
                    mod_act = st.text_input("Modified action", action.action, key=f"mod_act_{i}")
                    mod_cmd = st.text_input("Executed command", action.technical_command or "", key=f"mod_cmd_{i}")
                    if st.button("Approve modified fix", key=f"mod_btn_{i}", disabled=not can_approve):
                        out = engine.handle_accepted_fix(
                            selected_scenario_id, action.action_id, action.source_layer or "", action.action,
                            user_id=st.session_state.username, modified_action=mod_act, modified_command=mod_cmd,
                            root_cause_text=master.anchor_reference.primary_driver,
                            target_environment=action.target_environment or "production")
                        st.success(f"Playbook {out['playbook_entry']['id']} ingested into Layer 1.")
                        st.rerun()
        if not is_engineer:
            st.caption("Approving or denying fixes requires `SENIOR_ENGINEER` clearance; VP-level spend requires `EXECUTIVE_VP`.")

# ============================================================================ TAB 2
with tab2:
    st.subheader(":material/account_tree: Bounded causal DAG")
    st.caption(f"The Cage: [-{CONFIG.cage_pre_hours}h, +{CONFIG.cage_post_hours}h] window + region/platform match · "
               f"The Brakes: W ≥ {threshold:.2f}, max {CONFIG.max_traversal_hops} hops, "
               f"{CONFIG.hop_attenuation:.2f} attenuation per extra hop.")

    nodes = {n["id"]: n for n in dag_payload.nodes}
    pos = {dag_payload.anchor_id: (0.0, 0.0)}
    hop1 = [e for e in dag_payload.edges if e.target == dag_payload.anchor_id]
    for idx, e in enumerate(hop1):
        ang = 2 * math.pi * idx / max(1, len(hop1))
        pos[e.source] = (2.0 * math.cos(ang), 2.0 * math.sin(ang))
    for e in dag_payload.edges:
        if e.source not in pos and e.target in pos:
            px, py = pos[e.target]
            ang = math.atan2(py, px) + 0.35 * (len(pos) % 3 - 1)
            pos[e.source] = (px + 1.6 * math.cos(ang), py + 1.6 * math.sin(ang))

    fig = go.Figure()
    for e in dag_payload.edges:
        if e.source in pos and e.target in pos:
            (x0, y0), (x1, y1) = pos[e.source], pos[e.target]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="text",
                text=f"{e.relation} · W={e.weight:.2f}",
                line=dict(width=1 + 4 * max(e.weight, 0.05), color="#94A3B8" if e.relation == "historical_context" else "#60A5FA",
                          dash="dot" if e.relation in ("historical_context", "corroborates") else "solid")))
    colors, xs, ys, labels, hovers = [], [], [], [], []
    for nid, (x, y) in pos.items():
        n = nodes.get(nid, {})
        xs.append(x)
        ys.append(y)
        labels.append(nid)
        hovers.append(f"<b>{n.get('label', nid)}</b><br>{n.get('type', '')}<br>{str(n.get('content', ''))[:90]}")
        if n.get("is_anchor"):
            colors.append("#F87171")
        elif str(n.get("type", "")).startswith("Historical"):
            colors.append("#94A3B8")
        elif n.get("is_masked"):
            colors.append("#FBBF24")
        else:
            colors.append("#34D399" if n.get("hop", 1) == 1 else "#A78BFA")
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=labels, textposition="bottom center",
                             hovertext=hovers, hoverinfo="text",
                             marker=dict(size=30, color=colors, line=dict(width=2, color="#0F172A"))))
    fig.update_layout(showlegend=False, height=460, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    st.plotly_chart(fig)
    st.caption("Red: anchor · green: hop-1 driver · purple: hop-2 driver/corroboration · yellow: masked · grey dotted: institutional memory.")

    st.subheader(":material/calculate: Causal scoring decomposition (W = CR × CI)")
    rows = []
    for node, w, cr, ci, tier, details in scored_nodes:
        historical = node.node_type.value.startswith("Historical")
        rows.append({
            "Node": node.node_id, "Title": node.title,
            "Wt": details.get("Wt"), "We": details.get("We"), "Ws": details.get("Ws"),
            "CR": round(cr, 3), "Wcf": details.get("w_cf"), "CI": round(ci, 3), "W": round(w, 3),
            "Tier": tier,
            "Status": ("Institutional memory" if historical else
                       "Surviving evidence" if any(n.node_id == node.node_id for n in surviving_nodes) else
                       f"Discarded (W < {threshold:.2f})"),
        })
    st.dataframe(pd.DataFrame(rows))

    math_ = ctx.get("metric_tree_math")
    if math_:
        st.markdown("#### Multivariate metric tree")
        st.latex(r"\Delta R = P \cdot \Delta V + V \cdot \Delta P + \Delta P \cdot \Delta V")
        st.info(f"Price effect ${math_.get('price_effect_usd', 0):,.2f} · Volume effect ${math_.get('volume_effect_usd', 0):,.2f} · "
                f"Interaction ${math_.get('interaction_effect_usd', 0):,.2f} · Total ΔR ${math_.get('total_delta_r_usd', 0):,.2f}")
    shap = ctx.get("shap_attribution")
    if shap:
        st.markdown(f"#### SHAP attribution on the global model ({shap.get('model_type')}, train R² {shap.get('train_r2')})")
        sdf = pd.DataFrame({"feature": list(shap["shap_values"]), "SHAP (USD)": list(shap["shap_values"].values())})
        st.bar_chart(sdf.set_index("feature"))
        st.caption(f"Base value ${shap['base_value']:,.0f} → prediction ${shap['prediction']:,.0f} "
                   f"(additivity gap {shap['additivity_gap']}) · {shap['method']}")

    with st.expander("Stage 1 detection report"):
        st.json(result.get("detection", {}))
    with st.expander("The Cage: pruned before scoring"):
        cr = result.get("cage_report", {})
        st.write({"temporal_window": cr.get("window"), "rejected": cr.get("rejected"),
                  "scoped_out_by_direction": result.get("scoped_out"), "scope_direction": ctx.get("scope_direction")})
    with st.expander("Discarded candidates"):
        for d in master.discarded_candidates:
            st.write(f"- **{d.action}** ({d.source_layer}) — {d.critic_verdict}")

# ============================================================================ TAB 3
with tab3:
    st.subheader(":material/rocket_launch: Blue-sky challenger (sandbox)")
    st.markdown("Channel B proposes one unconstrained strategic idea. The Reality Checker critiques it without "
                "rejecting it or looping the governance graph. Promotion requires `EXECUTIVE_VP` and a shadow run.")
    if not master.blue_sky_actions:
        st.info("No blue-sky ideas generated.")
    for idx, a in enumerate(master.blue_sky_actions):
        col_idea, col_critic = st.columns(2)
        with col_idea:
            st.warning(f"**{a.action}**\n\n- Cost: `${a.estimated_cost_usd:,.0f}`\n- Time to impact: `{a.time_to_impact_minutes} min`"
                       f"\n- Owner: {a.raci_owner}\n- Status: `{a.approval_status}`")
            if st.button(":material/upgrade: Promote to main", key=f"promote_bs_{idx}", disabled=not is_vp):
                block = a.model_copy(update={"approval_status": "PROMOTED_FROM_SANDBOX", "requires_shadow_run": True})
                st.session_state.setdefault("promoted", {}).setdefault(selected_scenario_id, []).append(block)
                engine.trust_tuner.record_feedback(a.action_id, a.source_layer or "Layer 5 - Blue-Sky", "ACCEPT",
                                                   st.session_state.username)
                st.success("Promoted to the executive tab (requires shadow run).")
                st.rerun()
        with col_critic:
            st.markdown("#### :material/psychology: Reality checker")
            st.info(a.critic_verdict or raw_state.get("blue_sky_critique", "No critique."))

# ============================================================================ TAB 4
with tab4:
    ev = master.engineer_view
    st.subheader(":material/terminal: Engineer view")
    st.markdown(f"**Technical root cause:** {ev.technical_root_cause}")
    st.markdown("**Evidence log stream**")
    st.code("\n".join(ev.system_logs), language="text")
    st.markdown(f"**Execution playbook** — target `{ev.execution_playbook.target_environment}`")
    st.code(ev.execution_playbook.command, language="bash")
    for extra in ev.additional_playbooks:
        st.caption(f"Alternative — target `{extra.target_environment}`")
        st.code(extra.command, language="bash")
    st.caption("Omnision is advisory: approved commands are handed to the RACI owner to run through the normal "
               "deployment pipeline, never executed automatically.")
    if master.ops_view:
        st.subheader(":material/support_agent: Ops view")
        st.markdown(f"**Bottleneck:** {master.ops_view.operational_bottleneck}")
        st.markdown(f"**SLA impact:** {master.ops_view.sla_impact}")
        for step in master.ops_view.mitigation_steps:
            st.markdown(f"- {step}")

# ============================================================================ TAB 5
with tab5:
    rt = master.runtime_metadata
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Latency", f"{rt.execution_latency_ms} ms")
    k2.metric("Tokens (in / out)", f"{rt.input_tokens:,} / {rt.output_tokens:,}")
    k3.metric("Estimated cost", f"${rt.estimated_cost_usd:.4f}")
    k4.metric("Semantic cache", "HIT" if rt.cache_hit else "MISS")
    st.caption(f"Model routed: {rt.model_routed} · swarm iterations: {rt.swarm_iterations} · "
               f"LLM cache hits: {rt.llm_cache_hits} · budget pruning: {rt.budget_pruning_applied}")

    st.markdown("### :material/smart_toy: Agent trust weights (Wm)")
    st.caption("ACCEPT: Wm × (1 + η_boost) · REJECT: Wm × (1 − η_decay). Weights rank the next run's proposals.")
    st.bar_chart(pd.DataFrame(list(engine.supervisor.swarm.model_weights.items()),
                              columns=["agent", "Wm"]).set_index("agent"))
    if engine.trust_tuner.feedback_log:
        st.dataframe(pd.DataFrame(engine.trust_tuner.feedback_log))

    st.markdown("### :material/history_edu: Human corrections")
    st.write({
        "semantic_threshold": engine.cr_scorer.semantic_threshold,
        "verified_drivers": {k: v.node_id for k, v in engine.verified_drivers.items()},
        "demoted_nodes": {k: sorted(v) for k, v in engine.demoted_nodes.items()},
        "rejected_fixes": engine.rejected_actions,
    })
    if engine.rca_corrector.override_history:
        st.dataframe(pd.DataFrame(engine.rca_corrector.override_history))

    st.markdown("### :material/library_books: Layer 1 playbooks")
    st.dataframe(pd.DataFrame([{k: p.get(k) for k in ("id", "trigger_pattern", "action", "required_lever", "cost_usd", "raci")}
                               for p in engine.layers_store.layer_1_playbooks]))

    with st.expander("Raw unified master payload (JSON)"):
        st.json(master.model_dump(mode="json"))
