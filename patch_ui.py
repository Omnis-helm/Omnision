import os

path = r"D:\projects\Omnision\Omnision\kpi_engine\ui\streamlit_app.py"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    code = f.read()

# 1. Clean up overall Mojibake (corrupted characters)
code = code.replace("Ã‚Â§", "§")
code = code.replace("Ã¢â‚¬Â¢", "-")

# The lock symbol got mangled before
code = code.replace("st.title(\"dY\"' Omnision Secure Login\")", 'st.title("\\U0001F512 Omnision Secure Login")')
code = code.replace("st.title(\"🔒 Omnision Secure Login\")", 'st.title("\\U0001F512 Omnision Secure Login")')
# Ensure no lingering weird chars
code = code.replace("dY'¤", "\\U0001F464")
code = code.replace("dY>ï¸,", "\\U0001F6E1")
code = code.replace("Ã¢â‚¬Â¢", "-")
code = code.replace("ðŸ'¤", "\\U0001F464")
code = code.replace("ðŸ>ï¸,", "\\U0001F6E1")

# Clean the tab definitions (in case they have emojis hardcoded)
code = code.replace("tab1, tab2, tab3, tab4 = st.tabs([", "tab1, tab2, tab3 = st.tabs([")
code = code.replace("\"dY\"~ Executive Action Plan\",", "\"\\U0001F4D6 Executive Action Plan\",")
code = code.replace("\"dY 📐 Engineering View\",", "\"\\U0001F4C8 Engineering View\",")
code = code.replace("\"dY>,? Blue-Sky Sandboxing\",", "\"\\U0001F6E0 Blue-Sky Sandboxing\",")
code = code.replace("\"dY\"o Human RCA Override\"", "")
# Also handle the original emojis if they were correct
code = code.replace("\"📖 Executive Action Plan\",", "\"\\U0001F4D6 Executive Action Plan\",")
code = code.replace("\"📐 Engineering View\",", "\"\\U0001F4C8 Engineering View\",")
code = code.replace("\"⚙️ Blue-Sky Sandboxing\",", "\"\\U0001F6E0 Blue-Sky Sandboxing\",")
code = code.replace("\"⚖️ Human RCA Override\"", "")

# Remove trailing comma in tabs list if present
code = code.replace("Blue-Sky Sandboxing\", ]", "Blue-Sky Sandboxing\"]")
code = code.replace("Blue-Sky Sandboxing\",]", "Blue-Sky Sandboxing\"]")
code = code.replace("Blue-Sky Sandboxing\",  ]", "Blue-Sky Sandboxing\"]")

# Redo TAB 3 and remove TAB 4
tab3_start = code.find("    with tab3:")
tab5_start = code.find("    # ==================== TAB 5", tab3_start)
if tab5_start == -1: tab5_start = len(code)

new_tab3 = """    with tab3:
        st.subheader(":material/rocket_launch: Blue-sky LLM challenger & solution network (\\u00A73.2, \\u00A78)")
        st.markdown(\"\"\"
        Omnision executes an unconstrained challenger path:
        * **Channel B (Challenger Path):** Acts as an unconstrained turnaround CEO generating out-of-the-box strategic fixes.
        * **The Critic Governance:** An independent evaluator cross-examines all ideas against operational levers and budget limits before anything reaches a stakeholder.
        \"\"\")

        blue_sky_proposals = result.get("raw_state", {}).get("blue_sky_proposals", [])
        blue_sky_critique = result.get("raw_state", {}).get("blue_sky_critique", "No critique generated.")
        
        if blue_sky_proposals:
            for idx, a in enumerate(blue_sky_proposals):
                col_idea, col_critic = st.columns(2)
                
                with col_idea:
                    st.markdown("### :material/lightbulb: Blue-Sky Solution")
                    st.warning(f"**{a.get('action')}**\\n\\n- Cost: `${float(a.get('estimated_cost_usd', 0)):,.2f}`\\n\\n- Approval: `{a.get('approval_status')}`")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(":material/refresh: Rerun", key=f"rerun_bs_{idx}"):
                            st.success("Blue-Sky rerolled! (Simulated)")
                    with b2:
                        if st.button(":material/upgrade: Promote to Main", key=f"promote_bs_{idx}"):
                            from kpi_engine.governor.schemas import RecommendedActionBlock
                            new_action = RecommendedActionBlock(
                                action_id=a.get("action_id", "ACT-BS"),
                                action=a.get("action"),
                                estimated_cost_usd=float(a.get("estimated_cost_usd", 0)),
                                time_to_impact_minutes=int(a.get("time_to_impact_minutes", 0)),
                                expected_damage_reverted="Unknown",
                                raci_owner=a.get("raci_owner", "System"),
                                approval_status="PROMOTED_FROM_SANDBOX",
                                source_layer="Layer 5 - Blue-Sky",
                                model_confidence_weight=0.9,
                                critic_verdict=blue_sky_critique,
                                requires_shadow_run=True
                            )
                            new_result = dict(result)
                            new_result["master_payload"].executive_view.recommended_actions.append(new_action)
                            st.session_state.override_result = new_result
                            st.success("Appended to Main Executive Tab!")
                            st.rerun()

                with col_critic:
                    st.markdown("### :material/psychology: The Reality Checker")
                    st.info(f"**Critic Verdict:**\\n\\n{blue_sky_critique}")
        else:
            st.info("No Blue-Sky actions generated.")

"""

# Stitch it all together, cutting out the old tab 3 and tab 4 entirely
new_code = code[:tab3_start] + new_tab3 + code[tab5_start:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_code)
print("Updated streamlit_app.py")
