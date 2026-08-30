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
    page_title="Omnision — KPI Storytelling Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for executive polish
st.markdown("""
<style>
    .omnision-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .omnision-sub {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .card-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
    }
    .badge-approved {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
    }
    .badge-vp {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
    }
    .badge-discarded {
        background-color: #F3F4F6;
        color: #4B5563;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Singleton Engine in Session State
if "engine" not in st.session_state:
    st.session_state.engine = KPIStorytellingEngine()

engine: KPIStorytellingEngine = st.session_state.engine

# Sidebar Configuration
st.sidebar.markdown("## ⚡ Omnision Control Center")
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

role_options = {
    "EXECUTIVE_VP": UserClearance.EXECUTIVE_VP,
    "SENIOR_ENGINEER": UserClearance.SENIOR_ENGINEER,
    "JUNIOR_ANALYST": UserClearance.JUNIOR_ANALYST,
}

selected_role_name = st.sidebar.selectbox(
    "Active User Clearance / Persona",
    options=list(role_options.keys()),
    index=0,
    key="omnision_role_selector",
)
active_role = role_options[selected_role_name]

force_refresh = st.sidebar.checkbox("Bypass Semantic Cache (Force Fresh Inference)", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Fleet Telemetry & Memory")
st.sidebar.metric("Cumulative Tokens Consumed", f"{engine.supervisor.cumulative_token_spend:,}")
st.sidebar.metric("Semantic Cached Payloads", f"{len(engine.supervisor.semantic_cache)}")
st.sidebar.metric("Active Layer 1 Playbooks", f"{len(engine.layers_store.layer_1_playbooks)}")

# Main Header
st.markdown('<div class="omnision-header">Omnision</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="omnision-sub">Autonomous Root-Cause Diagnosis · Multivariate Causal Inference · Multi-Agent Governance · Continuous Learning</div>',
    unsafe_allow_html=True,
)

# Execute Pipeline Safely
result = engine.run_pipeline(
    scenario_id=selected_scenario_id,
    user_role=active_role,
    force_refresh=force_refresh,
)

# ==================== HANDLE ABSTAINED STATE GRACEFULLY (WITHOUT GOING BLANK) ====================
if result.get("status") == "ABSTAINED":
    st.error("🛡️ **Omnision Security Boundary: Graceful Abstention Enforced**")
    
    col_s1, col_s2 = st.columns([3, 2])
    with col_s1:
        st.markdown(f"### ⚠️ {result.get('reason')}")
        st.markdown("""
        **Why this happened (§2.3 / §4.3 Hybrid Security Matrix):**
        * The primary root cause of this anomaly is classified under **Tier 1 Strategic Domain Pruning** (e.g. unannounced M&A, HR terminations, executive due diligence).
        * Your active role (`""" + selected_role_name + """`) lacks `EXECUTIVE_VP` clearance.
        * Under Omnision's mathematical integrity rules, rather than hallucinating a false secondary cause or presenting an incomplete equation, the engine **gracefully abstains**.
        """)
        if st.button("🔓 Elevate Clearance to EXECUTIVE_VP", type="primary"):
            st.session_state["omnision_role_selector"] = "EXECUTIVE_VP"
            st.rerun()

    with col_s2:
        st.markdown("### 🔒 Security Audit Receipt")
        st.json(result.get("security_audit", {}))
        
    st.markdown("---")
    st.info("💡 Tip: Select **Executive VP** in the sidebar or click the button above to view the full cleared investigation.")

else:
    # ==================== SUCCESS STATE: FULL MULTI-PERSONA EXPLORER ====================
    anchor = result["anchor"]
    master: UnifiedMasterPayload = result["master_payload"]
    dag_payload = result.get("dag_payload")
    scored_nodes = result.get("scored_nodes", [])
    surviving_nodes = result.get("surviving_evidence", [])
    discarded_noise = result.get("discarded_noise", [])

    # Top KPI Metrics Strip
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Executive Narrative",
        "🔍 Causal DAG & Math Proofs",
        "🛠️ DevOps & Operations View",
        "🚀 Blue-Sky Challenger & Solutions",
        "🧠 Human RCA Override Sandbox",
        "📈 Telemetry & Learning Loop",
    ])

    # ==================== TAB 1: EXECUTIVE VIEW ====================
    with tab1:
        st.subheader("👔 Executive Decision Brief")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Financial Exposure:** `${master.executive_view.financial_impact_usd:,.2f} USD`")
        with col2:
            risk_badge = f'<span class="badge-high">{master.executive_view.business_risk_level} RISK</span>'
            st.markdown(f"**Business Risk Rating:** {risk_badge}", unsafe_allow_html=True)
        with col3:
            st.markdown(f"**Primary Driver:** `{master.anchor_reference.primary_driver}`")
            st.caption(f"Causal Weight: **{master.anchor_reference.causal_weight:.2f}** | Security: `{master.anchor_reference.security_applied}`")

        st.markdown("### 📋 Governed Action Recommendations")
        st.caption("Cross-examined by The Critic against technical levers, SLA limits, and RACI budget ceilings.")

        if master.executive_view.recommended_actions:
            for i, action in enumerate(master.executive_view.recommended_actions):
                with st.container():
                    st.markdown(f"#### #{i+1} {action.action}")
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                    with c1:
                        st.write(f"**Source:** {action.source_layer}")
                        st.write(f"**Critic Verdict:** `{action.critic_verdict}`")
                    with c2:
                        st.write(f"**Est. Cost:** `${action.estimated_cost_usd:,.2f}`")
                        st.write(f"**Time-to-Impact:** `{action.time_to_impact_minutes} mins`")
                    with c3:
                        st.write(f"**RACI Owner:** `{action.raci_owner}`")
                        status_html = f'<span class="badge-approved">{action.approval_status}</span>' if action.approval_status == "AUTO_APPROVED" else f'<span class="badge-vp">{action.approval_status}</span>'
                        st.markdown(f"**Approval Status:** {status_html}", unsafe_allow_html=True)
                    with c4:
                        st.write("**Continuous Learning Feedback:**")
                        fb_col1, fb_col2 = st.columns(2)
                        with fb_col1:
                            if st.button("✅ Accept", key=f"btn_acc_{action.action_id}_{i}"):
                                rec = engine.trust_tuner.record_feedback(action.action_id, action.source_layer or "", "ACCEPT")
                                st.success(f"Trust boosted to {rec['new_weight']:.4f}")
                        with fb_col2:
                            if st.button("❌ Reject", key=f"btn_rej_{action.action_id}_{i}"):
                                rec = engine.trust_tuner.record_feedback(action.action_id, action.source_layer or "", "REJECT")
                                st.error(f"Trust decayed to {rec['new_weight']:.4f}")
                    st.divider()
        else:
            st.info("No approved actions generated.")

    # ==================== TAB 2: CAUSAL DAG & MATH PROOFS ====================
    with tab2:
        st.subheader("🔍 Localized Causal DAG & Mathematical Proofs")
        st.caption("Just-in-Time Graph-RAG: Bounded by The Cage ([-48h, +12h]), max 2 hops, and threshold pruning (W ≥ 0.65).")

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
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🧮 Causal Scoring Decomposition Table")
        df_rows = []
        for item in scored_nodes:
            node, w, cr, ci, tier, details = item
            df_rows.append({
                "Node ID": node.node_id,
                "Title": node.title,
                "Contextual Relevance (CR)": f"{cr:.3f}",
                "Causal Impact (CI)": f"{ci:.3f}",
                "Composite Weight W = CR × CI": f"{w:.3f}",
                "Counterfactual Tier": tier,
                "Status": "Surviving Evidence (W ≥ 0.65)" if w >= 0.65 else "Discarded Noise (W < 0.65)",
            })
        st.dataframe(pd.DataFrame(df_rows), use_container_width=True)

        if selected_scenario_id == "SCENARIO_2_MULTIVARIATE_DAG_SHAP":
            st.markdown("#### 📐 Multivariate DAG Interaction Math (§2.5.3, §5.3.4)")
            st.latex(r"\Delta R = P \cdot \Delta V + V \cdot \Delta P + \Delta P \cdot \Delta V")
            st.info("Price Effect: -$28,000.00 | Volume Effect: -$21,740.00 | Joint Interaction: +$1,739.20 | Total ΔR = -$48,000.80")

    # ==================== TAB 3: DEVOPS & OPERATIONS VIEW ====================
    with tab3:
        st.subheader("🛠️ Federated DevOps & Operations View")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🖥️ Engineer View (Technical Playbook)")
            st.write(f"**Technical Root Cause:** `{master.engineer_view.technical_root_cause}`")
            st.write(f"**Target Environment:** `{master.engineer_view.execution_playbook.target_environment}`")
            st.code(master.engineer_view.execution_playbook.command, language="bash")
            st.write("**Associated System Logs:**")
            for log in master.engineer_view.system_logs:
                st.caption(f"• `{log}`")

        with col2:
            st.markdown("### ⚙️ Operations View (SLA & Routing)")
            if master.ops_view:
                st.write(f"**Operational Bottleneck:** {master.ops_view.operational_bottleneck}")
                st.write(f"**SLA Impact:** {master.ops_view.sla_impact}")
                st.write("**Mitigation Steps:**")
                for step in master.ops_view.mitigation_steps:
                    st.caption(f"• {step}")

    # ==================== TAB 4: BLUE-SKY CHALLENGER & SOLUTIONS ====================
    with tab4:
        st.subheader("🚀 Blue-Sky LLM Challenger & Solution Network (§3.2, §8)")
        st.markdown("""
        Omnision executes two parallel prompt channels simultaneously to expand ideas:
        * **Channel A (Grounded Path):** Resolves the incident strictly using internal SOPs, runbooks, and active operational levers.
        * **Channel B (Challenger Path):** Acts as an unconstrained turnaround CEO generating out-of-the-box strategic fixes.
        * **The Critic Governance:** An independent evaluator cross-examines all ideas against Layer 3 operational levers and Layer 4 budget limits before anything reaches a stakeholder.
        """)

        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.markdown("### 🛡️ Channel A: Grounded Solutions")
            grounded_actions = [a for a in master.executive_view.recommended_actions if "Challenger" not in a.source_layer]
            if grounded_actions:
                for a in grounded_actions:
                    st.success(f"**{a.action}**\n\n• Source: {a.source_layer}\n\n• Cost: `${a.estimated_cost_usd:,.2f}` | Time: `{a.time_to_impact_minutes}m`\n\n• Critic: `{a.critic_verdict}`")
            else:
                st.info("No grounded actions generated.")

        with col_ch2:
            st.markdown("### 💡 Channel B: Blue-Sky Challenger Solutions")
            challenger_actions = [a for a in master.executive_view.recommended_actions if "Challenger" in a.source_layer]
            if challenger_actions:
                for a in challenger_actions:
                    st.warning(f"**{a.action}** (Passed Critic)\n\n• Cost: `${a.estimated_cost_usd:,.2f}`\n\n• Approval: `{a.approval_status}`")
            else:
                st.info("Challenger candidate was cross-examined by The Critic:")

            # Show discarded challenger solutions
            for d in master.discarded_candidates:
                if "Challenger" in d.source_layer:
                    st.error(f"**Action:** {d.action}\n\n• **Layer:** {d.source_layer}\n\n• **The Critic Rejection Verdict:** `{d.critic_verdict}`")

    # ==================== TAB 5: HUMAN RCA OVERRIDE SANDBOX ====================
    with tab5:
        st.subheader("🧠 Human-in-the-Loop RCA Override & Supervisor Invalidation Cascade")
        st.markdown("Auditing foundational diagnostic math: Demote incorrect causes, promote alternative evidence, or inject domain knowledge.")

        override_type = st.radio("Override Strategy", ["Select from Discarded Noise", "Inject Brand New Root Cause"], key="rca_strat_rad")

        primary_node_id = surviving_nodes[0].node_id if surviving_nodes else (scored_nodes[0][0].node_id if scored_nodes else "NODE-SYS-101")

        if override_type == "Select from Discarded Noise":
            if discarded_noise:
                noise_options = {n.node_id: f"{n.node_id}: {n.title}" for n in discarded_noise}
                selected_noise_id = st.selectbox("Promote Discarded Node to Primary Driver", options=list(noise_options.keys()), format_func=lambda x: noise_options[x])
                if st.button("🚀 Trigger Invalidation Cascade & Recalibrate", type="primary"):
                    res = engine.handle_human_rca_override(
                        scenario_id=selected_scenario_id,
                        demoted_node_id=primary_node_id,
                        promoted_node_id=selected_noise_id,
                        user_role=active_role,
                    )
                    st.success("Supervisor Invalidation Cascade complete! Swarm regenerated.")
                    st.json(res.get("recalibration_record", {}))
            else:
                st.info("No discarded noise nodes in this scenario to promote.")
        else:
            custom_rca = st.text_area("Custom Root Cause Diagnosis", value="Critical connection pool saturation on database cluster db-primary-01")
            if st.button("🚀 Inject Verified Cause & Regenerate Governed Actions", type="primary"):
                res = engine.handle_human_rca_override(
                    scenario_id=selected_scenario_id,
                    demoted_node_id=primary_node_id,
                    custom_injected_text=custom_rca,
                    user_role=active_role,
                )
                st.success("Human verified root cause injected! Fresh actions generated.")
                st.json(res.get("recalibration_record", {}))

    # ==================== TAB 6: TELEMETRY & CONTINUOUS LEARNING ====================
    with tab6:
        st.subheader("📈 LLM Economics, Telemetry & Continuous Learning Loop")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Execution Latency", f"{master.runtime_metadata.execution_latency_ms} ms")
        with m2:
            st.metric("Tokens Consumed", f"{master.runtime_metadata.total_tokens_consumed:,}")
        with m3:
            st.metric("Estimated Cost USD", f"${master.runtime_metadata.estimated_cost_usd:.4f}")
        with m4:
            st.metric("Semantic Cache Status", "HIT (0ms / $0)" if master.runtime_metadata.cache_hit else "MISS (Live LLM)")

        st.markdown("### 🤖 Model Confidence Trust Weights ($W_m$)")
        st.caption("Dynamically tuned via user feedback signals: W_m^(t+1) = W_m^(t) * (1 - η) on repeated rejections.")
        st.bar_chart(pd.DataFrame(list(engine.supervisor.swarm.model_weights.items()), columns=["Agent Model", "Trust Weight Wm"]).set_index("Agent Model"))

        st.markdown("### 📝 Dynamic Playbook Appends (Layer 1 Ingestion)")
        st.caption("Real-world engineer execution deltas captured and ingested into institutional memory.")
        with st.expander("➕ Test Dynamic Playbook Append"):
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
