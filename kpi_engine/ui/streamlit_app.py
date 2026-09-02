"""
Omnision: Autonomous KPI Storytelling & Causal Governance Engine (v3.0)
Interactive Executive Dashboard
"""

import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
import math
from datetime import datetime

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance, LifecycleStage
from kpi_engine.governor.schemas import UnifiedMasterPayload


st.set_page_config(
    page_title="Omnision â€” KPI Storytelling Engine",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS removed in favor of native config.toml theming

# Initialize Singleton Engine in Session State
if "engine" not in st.session_state:
    st.session_state.engine = KPIStorytellingEngine()

engine: KPIStorytellingEngine = st.session_state.engine

# Sidebar Configuration
st.sidebar.markdown("## :material/bolt: Omnision control center")
st.sidebar.markdown("**Unified Architecture Compendium v3.0**")

scenario_options = {
    "SCENARIO_1_STRIPE_GATEWAY_OUTAGE": "1. Stripe v4.1 Gateway Latency Outage (-12.4%)",
    "SCENARIO_2_MULTIVARIATE_DAG_SHAP": "2. Interacting Price & Volume Drivers (DAG + SHAP)",
    "SCENARIO_3_COLD_START_PHASED_HANDOVER": "3. Cold-Start 1-Click Mobile Checkout (<30d)",
    "SCENARIO_4_SECURITY_CLEARANCE_MATRIX": "4. Hybrid Security Matrix (Tier 1 & Tier 2)",
}

selected_scenario_id = st.sidebar.selectbox(
    "Select Benchmark Scenario",
    options=list(scenario_options.keys()),
    format_func=lambda x: scenario_options[x],
    key="omnision_scenario_selector",
)

# --- AUTHENTICATION MODULE ---
def load_users():
    users_path = PROJECT_ROOT / "kpi_engine" / "users.json"
    if users_path.exists():
        with open(users_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.active_role = "JUNIOR_ANALYST"

if not st.session_state.logged_in:
    st.title("🔒 Omnision Secure Login")
    st.markdown("Please log in to access the Autonomous Governance Engine.")
    users_db = load_users()
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username in users_db and users_db[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.active_role = users_db[username]["role"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop() # Halt execution until logged in

# Logout Button
st.sidebar.markdown(f"👤 **User:** `{st.session_state.username}`")
st.sidebar.markdown(f"🛡️ **Role:** `{st.session_state.active_role}`")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()
st.sidebar.markdown("---")

active_role = UserClearance[st.session_state.active_role]
# --- END AUTHENTICATION ---

# --- LLM CONFIGURATION (RBAC & SECURE SELECTION) ---
st.sidebar.markdown("### 🧠 AI Core Engine Selection")

provider_options = ["openai", "anthropic", "gemini", "ollama", "mock"]
public_providers = ["openai", "anthropic", "gemini"]

# Default to gemini if GOOGLE_API_KEY exists, otherwise mock
has_google = bool(os.getenv("GOOGLE_API_KEY") or getattr(CONFIG, "google_api_key", ""))
default_provider = "gemini" if has_google else "mock"
default_idx = provider_options.index(default_provider)

primary_llm = st.sidebar.selectbox("Primary LLM (RCA & Storytelling)", options=provider_options, index=default_idx)
bluesky_llm = st.sidebar.selectbox("Blue-Sky LLM (Shadow Ideation)", options=provider_options, index=default_idx)

if primary_llm in public_providers or bluesky_llm in public_providers:
    if st.session_state.active_role != "EXECUTIVE_VP":
        st.sidebar.error("🚨 **Access Level Not Met:** Public Cloud LLMs (OpenAI, Anthropic, Gemini) risk leaking internal telemetry data. Only `EXECUTIVE_VP` tier can authorize public LLM connections. Please select a private hosted LLM like `ollama` or `mock`.")
        st.stop() # Hard stop execution to prevent data leak

if not primary_llm or not bluesky_llm:
    st.sidebar.warning("Please select both a Primary and Blue-Sky LLM to run the engine.")
    st.stop()

# --- PRE-FLIGHT API KEY CHECKS ---
def check_api_key(provider):
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY") or CONFIG.openai_api_key
        if not key or not str(key).startswith("sk-") or len(str(key)) < 20:
            return False
    elif provider in ["anthropic", "claude"]:
        key = os.getenv("ANTHROPIC_API_KEY") or getattr(CONFIG, 'anthropic_api_key', '')
        if not key or not str(key).startswith("sk-ant-") or len(str(key)) < 20:
            return False
    elif provider in ["gemini", "google"]:
        key = os.getenv("GOOGLE_API_KEY") or getattr(CONFIG, 'google_api_key', '')
        if not key or len(str(key)) < 15:
            return False
    return True

for provider in [primary_llm, bluesky_llm]:
    if not check_api_key(provider):
        st.title("Omnision")
        st.error(f"🚨 **API Key invalid or not found for {provider}**")
        st.stop()

st.sidebar.markdown("---")

force_refresh = st.sidebar.checkbox("Bypass Semantic Cache (Force Fresh Inference)", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader(":material/monitoring: Fleet telemetry & memory")
st.sidebar.metric("Cumulative Tokens Consumed", f"{engine.supervisor.cumulative_token_spend:,}")
st.sidebar.metric("Semantic Cached Payloads", f"{len(engine.supervisor.semantic_cache)}")
st.sidebar.metric("Active Layer 1 Playbooks", f"{len(engine.layers_store.layer_1_playbooks)}")

# Main Header
st.title("Omnision")
st.caption("Autonomous Root-Cause Diagnosis Â· Multivariate Causal Inference Â· Multi-Agent Governance Â· Continuous Learning")

# Check if scenario changed, clear override_result if so
if st.session_state.get("current_scenario") != selected_scenario_id:
    st.session_state.current_scenario = selected_scenario_id
    st.session_state.pop("override_result", None)

# Execute Pipeline Safely
try:
    if "override_result" in st.session_state and not force_refresh:
        result = st.session_state.override_result
    else:
        result = engine.run_pipeline(
            scenario_id=selected_scenario_id,
            user_role=active_role,
            force_refresh=force_refresh,
            primary_llm=primary_llm,
            bluesky_llm=bluesky_llm,
        )
except Exception as e:
    error_msg = str(e)
    if "API Key not found" in error_msg:
        st.error(f"🚨 **Configuration Error:** {error_msg}")
    else:
        st.error(f"🚨 **Execution Error:** {error_msg}")
    st.stop()

# ==================== HANDLE ABSTAINED STATE GRACEFULLY (WITHOUT GOING BLANK) ====================
if result.get("status") == "ABSTAINED":
    st.error("ðŸ›¡ï¸ **Omnision Security Boundary: Graceful Abstention Enforced**")
    
    col_s1, col_s2 = st.columns([3, 2])
    with col_s1:
        st.markdown(f"### âš ï¸ {result.get('reason')}")
        st.markdown("""
        **Why this happened (Â§2.3 / Â§4.3 Hybrid Security Matrix):**
        * The primary root cause of this anomaly is classified under **Tier 1 Strategic Domain Pruning** (e.g. unannounced M&A, HR terminations, executive due diligence).
        * Your active role (`""" + selected_role_name + """`) lacks `EXECUTIVE_VP` clearance.
        * Under Omnision's mathematical integrity rules, rather than hallucinating a false secondary cause or presenting an incomplete equation, the engine **gracefully abstains**.
        """)
        def elevate_clearance():
            st.session_state["omnision_role_selector"] = "EXECUTIVE_VP"
            
        st.button("ðŸ”“ Elevate Clearance to EXECUTIVE_VP", type="primary", on_click=elevate_clearance)

    with col_s2:
        st.markdown("### ðŸ”’ Security Audit Receipt")
        st.json(result.get("security_audit", {}))
        
    st.markdown("---")
    st.info("ðŸ’¡ Tip: Select **Executive VP** in the sidebar or click the button above to view the full cleared investigation.")

else:
    # ==================== SUCCESS STATE: FULL MULTI-PERSONA EXPLORER ====================
    anchor = result["anchor"]
    master: UnifiedMasterPayload = result["master_payload"]
    dag_payload = result.get("dag_payload")
    scored_nodes = result.get("scored_nodes", [])
    surviving_nodes = result.get("surviving_evidence", [])
    discarded_noise = result.get("discarded_noise", [])

    # Top KPI Metrics Strip
    st.html("""
    <style>
    [data-testid="stMetricValue"] > div,
    [data-testid="stMetricLabel"] > div {
        font-size: 1.1rem !important;
        white-space: normal !important;
        word-break: break-word !important;
        line-height: 1.2 !important;
    }
    </style>
    """)
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    with col_a:
        st.metric("Anchor Metric", anchor.kpi_id)
    with col_b:
        st.metric("Current Value", f"{anchor.current_value:.2f}", f"{anchor.variance_pct:+.2f}%")
    with col_c:
        st.metric("Z-Score Shock", f"Z = {anchor.z_score:.2f}", "Severe Shock" if anchor.z_score >= 5.0 else "Anomaly Alert")
    with col_d:
        st.metric("Lifecycle Stage", anchor.lifecycle_stage.value)
    with col_e:
        st.metric("Security Applied", master.anchor_reference.security_applied)

    st.markdown("---")

    # Main Tab Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":material/summarize: Executive narrative",
        ":material/account_tree: Causal DAG & math proofs",
        ":material/rocket_launch: Blue-sky challenger & solutions",
        ":material/psychology: Human RCA override sandbox",
        ":material/insights: Telemetry & learning loop",
    ])

    # ==================== TAB 1: EXECUTIVE VIEW ====================
    with tab1:
        st.subheader(":material/assignment_ind: Executive decision brief")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Financial Exposure:** `${master.executive_view.financial_impact_usd:,.2f} USD`")
        with col2:
            st.markdown(f"**Business Risk Rating:** :red-badge[{master.executive_view.business_risk_level} RISK]")
        with col3:
            st.markdown(f"**Causal Weight:** **{master.anchor_reference.causal_weight:.2f}** | Security: `{master.anchor_reference.security_applied}`")

        st.markdown("---")
        
        # Two-column interactive table
        rca_col, fix_col = st.columns(2)
        
        with rca_col:
            st.markdown("### 🔍 Root Cause Analysis (RCA)")
            st.info(f"**Suggested Root Cause:**\n\n{master.anchor_reference.primary_driver}")
            
            # RCA Actions
            r1, r2 = st.columns(2)
            with r1:
                if st.button(":material/check_circle: Approve RCA", key="approve_rca", use_container_width=True):
                    st.success("RCA Approved.")
            with r2:
                if st.button(":material/cancel: Deny RCA", key="deny_rca", use_container_width=True):
                    # Trigger RCA Invalid Cascade (promote next node if any)
                    primary_node_id = surviving_nodes[0].node_id if surviving_nodes else (scored_nodes[0][0].node_id if scored_nodes else "NODE-SYS-101")
                    next_node_id = surviving_nodes[1].node_id if len(surviving_nodes) > 1 else None
                    if next_node_id:
                        res = engine.handle_human_rca_override(
                            scenario_id=selected_scenario_id,
                            demoted_node_id=primary_node_id,
                            promoted_node_id=next_node_id,
                            user_role=active_role,
                            primary_llm=primary_llm,
                            bluesky_llm=bluesky_llm,
                        )
                        new_result = dict(result)
                        new_result["master_payload"] = res["master_payload"]
                        new_result["surviving_evidence"] = [res["verified_driver"]] + [n for n in new_result.get("surviving_evidence", []) if n.node_id != res["verified_driver"].node_id and n.node_id != primary_node_id and n.node_id != next_node_id]
                        st.session_state.override_result = new_result
                        
                        st.session_state.engine = engine  # Ensure state is updated
                        st.success("RCA Denied. Swarm regenerated with next best evidence.")
                        st.rerun()
                    else:
                        st.error("No alternative evidence nodes available to promote.")
                        
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("#### Manual RCA Override")
            custom_rca = st.text_input("Inject Human Knowledge:", placeholder="Enter verified root cause...", key="custom_rca_input")
            if st.button("Submit Manual RCA", use_container_width=True):
                if custom_rca:
                    primary_node_id = surviving_nodes[0].node_id if surviving_nodes else (scored_nodes[0][0].node_id if scored_nodes else "NODE-SYS-101")
                    res = engine.handle_human_rca_override(
                        scenario_id=selected_scenario_id,
                        demoted_node_id=primary_node_id,
                        custom_injected_text=custom_rca,
                        user_role=active_role,
                        primary_llm=primary_llm,
                        bluesky_llm=bluesky_llm,
                    )
                    new_result = dict(result)
                    new_result["master_payload"] = res["master_payload"]
                    new_result["surviving_evidence"] = [res["verified_driver"]] + [n for n in new_result.get("surviving_evidence", []) if n.node_id != res["verified_driver"].node_id and n.node_id != primary_node_id]
                    st.session_state.override_result = new_result
                    
                    st.session_state.engine = engine
                    st.success("Manual RCA injected! Swarm regenerated.")
                    st.rerun()


        with fix_col:
            st.markdown("### 🛠️ Mitigation Action (Fixes)")
            if master.executive_view.recommended_actions:
                for i, action in enumerate(master.executive_view.recommended_actions):
                    st.success(f"**Suggested Fix:**\n\n{action.action}")
                    
                    st.markdown("**Expected Impact & Cost:**")
                    st.markdown(f"- ⏳ **Time to Fix:** `{action.time_to_impact_minutes} mins`")
                    st.markdown(f"- 💰 **Cost:** `${action.estimated_cost_usd:,.2f}`")
                    st.markdown(f"- 📈 **Damage Reverted:** `{action.expected_damage_reverted or 'Unknown'}`")
                    
                    f1, f2 = st.columns(2)
                    with f1:
                        if st.button(":material/check_circle: Approve Fix", key=f"approve_fix_{i}", use_container_width=True):
                            st.success("Fix Approved for execution.")
                    with f2:
                        if st.button(":material/cancel: Deny Fix", key=f"deny_fix_{i}", use_container_width=True):
                            primary_driver = surviving_nodes[0] if surviving_nodes else (scored_nodes[0][0] if scored_nodes else None)
                            res = engine.handle_rejected_fix(
                                scenario_id=selected_scenario_id,
                                primary_driver=primary_driver,
                                rejected_action_text=action.action,
                                user_role=active_role,
                                primary_llm=primary_llm,
                                bluesky_llm=bluesky_llm,
                            )
                            new_result = dict(result)
                            new_result["master_payload"] = res["master_payload"]
                            st.session_state.override_result = new_result
                            
                            st.session_state.engine = engine
                            st.success("Fix Denied. Swarm regenerated new mitigation actions.")
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No recommended actions generated.")
                
            st.markdown("---")
            st.markdown("#### Manual Fix Override")
            st.caption("Inject Human Knowledge:")
            custom_fix = st.text_input("custom_fix_input", placeholder="e.g. Rollback deployment to v2.1", label_visibility="collapsed")
            if st.button("Submit Manual Fix", use_container_width=True):
                if custom_fix:
                    import time
                    from kpi_engine.governor.schemas import RecommendedActionBlock
                    new_action = RecommendedActionBlock(
                        action_id=f"ACT-MANUAL-{int(time.time())}",
                        action=custom_fix,
                        estimated_cost_usd=0.0,
                        time_to_impact_minutes=0,
                        raci_owner="Human Operator",
                        approval_status="PENDING_REVIEW",
                        source_layer="Layer 1 - Human Override",
                        critic_verdict="PASS - Manual Override",
                        expected_damage_reverted="Unknown",
                        requires_shadow_run=False
                    )
                    new_result = dict(result)
                    if not new_result.get("master_payload"):
                        pass # Safety check
                    elif not new_result["master_payload"].executive_view.recommended_actions:
                        new_result["master_payload"].executive_view.recommended_actions = [new_action]
                    else:
                        new_result["master_payload"].executive_view.recommended_actions.append(new_action)
                    st.session_state.override_result = new_result
                    st.success("Manual fix appended!")
                    st.rerun()


    # ==================== TAB 2: CAUSAL DAG & MATH PROOFS ====================
    with tab2:
        st.subheader(":material/account_tree: Localized causal DAG & mathematical proofs")
        st.caption("Just-in-Time Graph-RAG: Bounded by The Cage ([-48h, +12h]), max 2 hops, and threshold pruning (W â‰¥ 0.65).")

        fig = go.Figure()

        # Anchor node center
        node_x = [0.0]
        node_y = [0.0]
        node_text = [f"<b>[ANCHOR] {anchor.metric_name}</b><br>Drop: {anchor.variance_pct:.2f}%<br>Z-score: {anchor.z_score:.2f}"]
        node_color = ["#EF4444"]
        node_labels = [anchor.kpi_id]

        if surviving_nodes:
            for idx, node in enumerate(surviving_nodes):
                angle = (2.0 * math.pi * idx) / max(1, len(surviving_nodes))
                nx = 2.0 * math.cos(angle)
                ny = 2.0 * math.sin(angle)

                node_x.append(nx)
                node_y.append(ny)
                node_text.append(f"<b>{node.title}</b><br>{node.node_type.value}<br>{node.content[:60]}...")
                node_color.append("#3B82F6" if not node.is_masked else "#F59E0B")
                node_labels.append(node.node_id)

                fig.add_trace(go.Scatter(
                    x=[nx, 0.0],
                    y=[ny, 0.0],
                    mode="lines",
                    line=dict(width=3, color="#64748B"),
                    hoverinfo="none",
                ))

        fig.add_trace(go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(size=34, color=node_color, line=dict(width=2, color="#FFFFFF")),
            text=node_labels,
            textposition="bottom center",
            hovertext=node_text,
            hoverinfo="text",
    ))

        fig.update_layout(
            showlegend=False,
            height=420,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#F8FAFC",
    )
        st.plotly_chart(fig, width='stretch')

        st.subheader(":material/calculate: Causal scoring decomposition table")
        df_rows = []
        for item in scored_nodes:
            node, w, cr, ci, tier, details = item
            df_rows.append({
                "Node ID": node.node_id,
                "Title": node.title,
                "Contextual Relevance (CR)": f"{cr:.3f}",
                "Causal Impact (CI)": f"{ci:.3f}",
                "Composite Weight W = CR Ã— CI": f"{w:.3f}",
                "Counterfactual Tier": tier,
                "Status": "Surviving Evidence (W â‰¥ 0.65)" if w >= 0.65 else "Discarded Noise (W < 0.65)",
            })
        st.dataframe(pd.DataFrame(df_rows), width='stretch')

        if selected_scenario_id == "SCENARIO_2_MULTIVARIATE_DAG_SHAP":
            st.markdown("#### :material/architecture: Multivariate DAG interaction math (Â§2.5.3, Â§5.3.4)")
            st.latex(r"\Delta R = P \cdot \Delta V + V \cdot \Delta P + \Delta P \cdot \Delta V")
            st.info("Price Effect: -$28,000.00 | Volume Effect: -$21,740.00 | Joint Interaction: +$1,739.20 | Total Î”R = -$48,000.80")



    # ==================== TAB 3: BLUE-SKY CHALLENGER & SOLUTIONS ====================
    with tab3:
        st.subheader(":material/rocket_launch: Blue-sky LLM challenger & solution network (Â§3.2, Â§8)")
        st.markdown("""
        Omnision executes two parallel prompt channels simultaneously to expand ideas:
        * **Channel A (Grounded Path):** Resolves the incident strictly using internal SOPs, runbooks, and active operational levers.
        * **Channel B (Challenger Path):** Acts as an unconstrained turnaround CEO generating out-of-the-box strategic fixes.
        * **The Critic Governance:** An independent evaluator cross-examines all ideas against Layer 3 operational levers and Layer 4 budget limits before anything reaches a stakeholder.
        """)

        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.markdown("### :material/shield: Channel A: Grounded solutions")
            grounded_actions = [a for a in master.executive_view.recommended_actions if "Challenger" not in a.source_layer]
            if grounded_actions:
                for a in grounded_actions:
                    st.success(f"**{a.action}**\n\nâ€¢ Source: {a.source_layer}\n\nâ€¢ Cost: `${a.estimated_cost_usd:,.2f}` | Time: `{a.time_to_impact_minutes}m`\n\nâ€¢ Critic: `{a.critic_verdict}`")
            else:
                st.info("No grounded actions generated.")

        with col_ch2:
            st.markdown("### :material/lightbulb: Channel B: Blue-sky challenger solutions")
            challenger_actions = [a for a in master.executive_view.recommended_actions if "Challenger" in a.source_layer]
            if challenger_actions:
                for a in challenger_actions:
                    st.warning(f"**{a.action}** (Passed Critic)\n\nâ€¢ Cost: `${a.estimated_cost_usd:,.2f}`\n\nâ€¢ Approval: `{a.approval_status}`")
            else:
                st.info("Challenger candidate was cross-examined by The Critic:")

            # Show discarded challenger solutions
            for d in master.discarded_candidates:
                if "Challenger" in d.source_layer:
                    st.error(f"**Action:** {d.action}\n\nâ€¢ **Layer:** {d.source_layer}\n\nâ€¢ **The Critic Rejection Verdict:** `{d.critic_verdict}`")

    # ==================== TAB 4: HUMAN RCA OVERRIDE SANDBOX ====================
    with tab4:
        st.subheader(":material/psychology: Human-in-the-loop RCA override & supervisor invalidation cascade")
        st.markdown("Auditing foundational diagnostic math: Demote incorrect causes, promote alternative evidence, or inject domain knowledge.")

        override_type = st.radio("Override Strategy", ["Select from Discarded Noise", "Inject Brand New Root Cause"], key="rca_strat_rad")

        primary_node_id = surviving_nodes[0].node_id if surviving_nodes else (scored_nodes[0][0].node_id if scored_nodes else "NODE-SYS-101")

        if override_type == "Select from Discarded Noise":
            if discarded_noise:
                noise_options = {n.node_id: f"{n.node_id}: {n.title}" for n in discarded_noise}
                selected_noise_id = st.selectbox("Promote Discarded Node to Primary Driver", options=list(noise_options.keys()), format_func=lambda x: noise_options[x])
                if st.button(":material/rocket_launch: Trigger invalidation cascade & recalibrate", type="primary"):
                    res = engine.handle_human_rca_override(
                        scenario_id=selected_scenario_id,
                        demoted_node_id=primary_node_id,
                        promoted_node_id=selected_noise_id,
                        user_role=active_role,
                        primary_llm=primary_llm,
                        bluesky_llm=bluesky_llm,
                    )
                    new_result = dict(result)
                    new_result["master_payload"] = res["master_payload"]
                    new_result["surviving_evidence"] = [res["verified_driver"]] + [n for n in new_result.get("surviving_evidence", []) if n.node_id != res["verified_driver"].node_id and n.node_id != primary_node_id]
                    st.session_state.override_result = new_result
                    
                    st.success("Supervisor Invalidation Cascade complete! Swarm regenerated.")
                    st.json(res.get("recalibration_record", {}))
            else:
                st.info("No discarded noise nodes in this scenario to promote.")
        else:
            custom_rca = st.text_area("Custom Root Cause Diagnosis", value="Critical connection pool saturation on database cluster db-primary-01")
            if st.button(":material/rocket_launch: Inject verified cause & regenerate governed actions", type="primary"):
                res = engine.handle_human_rca_override(
                    scenario_id=selected_scenario_id,
                    demoted_node_id=primary_node_id,
                    custom_injected_text=custom_rca,
                    user_role=active_role,
                    primary_llm=primary_llm,
                    bluesky_llm=bluesky_llm,
                )
                new_result = dict(result)
                new_result["master_payload"] = res["master_payload"]
                new_result["surviving_evidence"] = [res["verified_driver"]] + [n for n in new_result.get("surviving_evidence", []) if n.node_id != res["verified_driver"].node_id and n.node_id != primary_node_id]
                st.session_state.override_result = new_result
                
                st.success("Human verified root cause injected! Fresh actions generated.")
                st.json(res.get("recalibration_record", {}))

    # ==================== TAB 5: TELEMETRY & CONTINUOUS LEARNING ====================
    with tab5:
        st.subheader(":material/insights: LLM economics, telemetry & continuous learning loop")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Execution Latency", f"{master.runtime_metadata.execution_latency_ms} ms")
        with m2:
            st.metric("Tokens Consumed", f"{master.runtime_metadata.total_tokens_consumed:,}")
        with m3:
            st.metric("Estimated Cost USD", f"${master.runtime_metadata.estimated_cost_usd:.4f}")
        with m4:
            st.metric("Semantic Cache Status", "HIT (0ms / $0)" if master.runtime_metadata.cache_hit else "MISS (Live LLM)")

        st.markdown("### :material/smart_toy: Model confidence trust weights ($W_m$)")
        st.caption("Dynamically tuned via user feedback signals: W_m^(t+1) = W_m^(t) * (1 - Î·) on repeated rejections.")
        st.bar_chart(pd.DataFrame(list(engine.supervisor.swarm.model_weights.items()), columns=["Agent Model", "Trust Weight Wm"]).set_index("Agent Model"))

        st.markdown("### :material/history_edu: Dynamic playbook appends (Layer 1 ingestion)")
        st.caption("Real-world engineer execution deltas captured and ingested into institutional memory.")
        with st.expander("Test dynamic playbook append", icon=":material/add:"):
            mod_act = st.text_input("Modified Action", "Roll back Stripe v4.1 gateway integration AND flush Redis cache")
            mod_cmd = st.text_input("Modified Command", "helm rollback stripe-gateway 4.0 && redis-cli FLUSHALL")
            if st.button("Ingest Human Delta into Layer 1"):
                entry = engine.playbook_appender.capture_execution_delta(
                    base_action_id="ACT-101",
                    original_action="Roll back Stripe v4.1 gateway integration",
                    modified_action=mod_act,
                    modified_command=mod_cmd,
                )
                st.success(f"New Playbook [{entry['id']}] ingested into Layer 1 Prescriptive Store!")
                st.json(entry)











