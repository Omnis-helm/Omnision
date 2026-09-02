import os
import re

# ==============================================================
# 1. FIX LANGGRAPH ORCHESTRATOR (Initialization & Fallback)
# ==============================================================
lo_path = r"D:\projects\Omnision\Omnision\kpi_engine\governor\langgraph_orchestrator.py"
with open(lo_path, "r", encoding="utf-8") as f:
    lo_code = f.read()

# Add blue_sky_proposals and blue_sky_critique to initial_state
init_state_target = """        "proposals": [],
        "supervisor_feedback": None,"""
init_state_replacement = """        "proposals": [],
        "blue_sky_proposals": [],
        "blue_sky_critique": "",
        "supervisor_feedback": None,"""
if "blue_sky_proposals" not in lo_code.split("initial_state = {")[1].split("}")[0]:
    lo_code = lo_code.replace(init_state_target, init_state_replacement)

# Update fallback execution to include blue_sky_critic_node
fallback_target = """    blue_res = blue_sky_node(state)
    state.update(blue_res)
    
    det_res = deterministic_validator_node(state)"""
fallback_replacement = """    blue_res = blue_sky_node(state)
    state.update(blue_res)
    
    bs_critic_res = blue_sky_critic_node(state)
    state.update(bs_critic_res)
    
    det_res = deterministic_validator_node(state)"""
if "blue_sky_critic_node(state)" not in lo_code:
    lo_code = lo_code.replace(fallback_target, fallback_replacement)

with open(lo_path, "w", encoding="utf-8") as f:
    f.write(lo_code)

# ==============================================================
# 2. FIX STREAMLIT UI (Mojibake & Remove Tab 4)
# ==============================================================
ui_path = r"D:\projects\Omnision\Omnision\kpi_engine\ui\streamlit_app.py"
with open(ui_path, "r", encoding="utf-8", errors="replace") as f:
    ui_code = f.read()

# Completely overwrite the sidebar block to guarantee no mojibake
sidebar_regex = re.compile(r'# Sidebar Configuration.*?# --- END AUTHENTICATION ---', re.DOTALL)
clean_sidebar = """# Sidebar Configuration
st.sidebar.markdown("## :material/bolt: Omnision control center")
st.sidebar.markdown("**Unified Architecture Compendium v3.0**")

scenario_options = {
    "SCENARIO_1_STRIPE_GATEWAY_OUTAGE": "1. Stripe v4.1 Gateway Latency Outage (-12.4%)",
    "SCENARIO_4_SECURITY_CLEARANCE_MATRIX": "4. Hybrid Security Matrix (Tier 1 & Tier 2)",
}

selected_scenario_id = st.sidebar.selectbox(
    "Select Benchmark Scenario",
    options=list(scenario_options.keys()),
    format_func=lambda x: scenario_options[x],
    index=0
)

# --- AUTHENTICATION STUB ---
if not st.session_state.get("logged_in", False):
    st.stop() # Halt execution until logged in

# Logout Button
st.sidebar.markdown(f":material/person: **User:** `{st.session_state.username}`")
st.sidebar.markdown(f":material/badge: **Role:** `{st.session_state.active_role}`")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()
st.sidebar.markdown("---")

active_role = UserClearance[st.session_state.active_role]
# --- END AUTHENTICATION ---"""
ui_code = sidebar_regex.sub(clean_sidebar, ui_code)

# Fix AI Core Engine Selection header and error messages
ai_core_regex = re.compile(r'st\.sidebar\.markdown\("### .*? AI Core Engine Selection"\)')
ui_code = ai_core_regex.sub('st.sidebar.markdown("### :material/settings: AI Core Engine Selection")', ui_code)

access_err_regex = re.compile(r'st\.sidebar\.error\(".*? \*\*Access Level Not Met:\*\*')
ui_code = access_err_regex.sub('st.sidebar.error("🛑 **Access Level Not Met:**', ui_code)

api_err_regex = re.compile(r'st\.error\(f".*? \*\*API Key invalid')
ui_code = api_err_regex.sub('st.error(f"🛑 **API Key invalid', ui_code)

tip_regex = re.compile(r'st\.info\(".*? Tip: Select')
ui_code = tip_regex.sub('st.info("💡 Tip: Select', ui_code)

# Remove Tab 4 ("Human RCA Override") from the st.tabs list
# It might look like: tab1, tab2, tab3 = st.tabs(["...", "...", "...", "Human RCA Override", "..."])
# Or previously I changed it to tab1, tab2, tab3 = st.tabs([...]) but it still had 4 tabs?
# Let's forcefully replace the tabs definition
tabs_regex = re.compile(r'tab1, tab2, tab3, tab4, tab5 = st\.tabs\(\[.*?\]\)', re.DOTALL)
clean_tabs = """tab1, tab2, tab3, tab5 = st.tabs([
        ":material/menu_book: Executive narrative",
        ":material/account_tree: Causal DAG & math proofs",
        ":material/rocket_launch: Blue-sky challenger & solutions",
        ":material/monitoring: Telemetry & learning"
    ])"""
ui_code = tabs_regex.sub(clean_tabs, ui_code)

# Just in case my previous patch left it as `tab1, tab2, tab3 = st.tabs([...])` due to a bad replace:
# Let's find `st.tabs([` and just replace that whole line to the closing bracket.
import ast
# We'll use a simpler replacement for the tabs line
ui_code = re.sub(r'tab1, tab2, tab3.*st\.tabs\(\[.*?\]\)', clean_tabs, ui_code, flags=re.DOTALL)

with open(ui_path, "w", encoding="utf-8") as f:
    f.write(ui_code)

print("Applied strict segregation rules and final UI fixes.")
