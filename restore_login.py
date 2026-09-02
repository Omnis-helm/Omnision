import os
import re

ui_path = r"D:\projects\Omnision\Omnision\kpi_engine\ui\streamlit_app.py"
with open(ui_path, "r", encoding="utf-8") as f:
    ui_code = f.read()

target = """# --- AUTHENTICATION STUB ---
if not st.session_state.get("logged_in", False):
    st.stop() # Halt execution until logged in

# Logout Button"""

replacement = """# --- AUTHENTICATION MODULE ---
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
    st.title("\\U0001F512 Omnision Secure Login")
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

# Logout Button"""

ui_code = ui_code.replace(target, replacement)

with open(ui_path, "w", encoding="utf-8") as f:
    f.write(ui_code)
print("Restored login form")
