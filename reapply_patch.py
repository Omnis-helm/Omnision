import os
import re

# 1. hybrid_supervisor.py
hs_path = r"D:\projects\Omnision\Omnision\kpi_engine\governor\hybrid_supervisor.py"
with open(hs_path, "r", encoding="utf-8") as f:
    hs_code = f.read()

critic_node = """
def blue_sky_critic_node(state: AgentState) -> Dict[str, Any]:
    \"\"\"Layer 2.5: Unconstrained Critic specifically for Blue-Sky ideas. Does NOT reject or loop.\"\"\"
    blue_sky_proposals = state.get(\"blue_sky_proposals\", [])
    if not blue_sky_proposals:
        return {}
        
    latest_bs = blue_sky_proposals[-1]
    provider = state.get(\"bluesky_llm_provider\", \"mock\")
    
    if provider in [\"mock\", \"local\"] or getattr(CONFIG, \"prefer_local_tools\", True):
        decision = \"EVALUATED\"
        reason = \"Sandbox Evaluation: Idea is creatively unrestricted but poses high operational risk.\"
    else:
        from kpi_engine.governor.llm_factory import get_llm
        llm = get_llm(provider=provider, temperature=0.2)
        prompt = (
            f\"You are the Omnision Reality Checker.\\n\"
            f\"Review this unconstrained Blue-Sky action: {latest_bs.get('action')}\\n\"
            f\"Provide a brief, 1-2 sentence constructive critique on its feasibility and risk. Do not reject it, just critique it.\\n\"
        )
        try:
            response = llm.invoke(prompt)
            reason = str(response.content).strip()
        except Exception as e:
            reason = f\"Critic parsing error: {str(e)}\"
    
    return {
        \"blue_sky_critique\": reason
    }
"""
if "blue_sky_critic_node" not in hs_code:
    hs_code += "\n" + critic_node
with open(hs_path, "w", encoding="utf-8") as f:
    f.write(hs_code)

# 2. llm_state.py
ls_path = r"D:\projects\Omnision\Omnision\kpi_engine\governor\llm_state.py"
with open(ls_path, "r", encoding="utf-8") as f:
    ls_code = f.read()
ls_code = ls_code.replace("blue_sky_proposals: Annotated[List[Dict[str, Any]], operator.add]", "blue_sky_proposals: Annotated[List[Dict[str, Any]], operator.add]\n    blue_sky_critique: str")
with open(ls_path, "w", encoding="utf-8") as f:
    f.write(ls_code)

# 3. langgraph_orchestrator.py
lo_path = r"D:\projects\Omnision\Omnision\kpi_engine\governor\langgraph_orchestrator.py"
with open(lo_path, "r", encoding="utf-8") as f:
    lo_code = f.read()

lo_code = lo_code.replace("from kpi_engine.governor.hybrid_supervisor import deterministic_validator_node, llm_supervisor_node", "from kpi_engine.governor.hybrid_supervisor import deterministic_validator_node, llm_supervisor_node, blue_sky_critic_node")
lo_code = lo_code.replace("workflow.add_node(\"llm_supervisor\", llm_supervisor_node)", "workflow.add_node(\"llm_supervisor\", llm_supervisor_node)\n            workflow.add_node(\"blue_sky_critic\", blue_sky_critic_node)")
lo_code = lo_code.replace("workflow.add_edge(\"rca_agent\", \"blue_sky_agent\")", "workflow.add_edge(\"rca_agent\", \"deterministic_validator\")\n            workflow.add_edge(\"rca_agent\", \"blue_sky_agent\")")
lo_code = lo_code.replace("workflow.add_edge(\"blue_sky_agent\", \"deterministic_validator\")", "workflow.add_edge(\"blue_sky_agent\", \"blue_sky_critic\")\n            workflow.add_edge(\"blue_sky_critic\", END)")

with open(lo_path, "w", encoding="utf-8") as f:
    f.write(lo_code)

# 4. pipeline.py
p_path = r"D:\projects\Omnision\Omnision\kpi_engine\pipeline.py"
with open(p_path, "r", encoding="utf-8") as f:
    p_code = f.read()

pipeline_replacement = """        # --- Multi-Action Extraction (Operational & Blue-Sky) ---
        from kpi_engine.governor.schemas import (
            ExecutiveViewBlock, 
            EngineerViewBlock, 
            OpsViewBlock, 
            RecommendedActionBlock,
            ExecutionPlaybookBlock
        )
        
        all_proposals = final_state.get("proposals", [])
        
        recommended_actions_list = []
        
        # Helper to process a proposal
        def process_proposal(prop, is_blue_sky=False):
            raw_action = prop.get("action", "No action returned")
            blocked_keywords = ["drop table", "delete from", "rm -rf", "chmod 777", "grant all"]
            if any(bad_word in raw_action.lower() for bad_word in blocked_keywords):
                return None
                
            est_cost = float(prop.get("estimated_cost_usd", 0.0))
            time_impact = int(prop.get("time_to_impact_minutes", 30))
            
            # Threshold checks
            if est_cost > context.get("vp_approval_required_cost_usd", 5000.0) and not is_blue_sky:
                return None
            if time_impact > 1440 and not is_blue_sky: # Exclude actions taking more than 24 hours unless blue-sky
                return None
                
            # If Blue-Sky, append critique from state
            critique = final_state.get("blue_sky_critique", "Uncritiqued Sandbox Idea.") if is_blue_sky else final_state.get("supervisor_feedback", "N/A")
            
            return RecommendedActionBlock(
                action_id=prop.get("action_id", "ACT-000"),
                action=raw_action,
                estimated_cost_usd=est_cost,
                time_to_impact_minutes=time_impact,
                expected_damage_reverted=f"{abs(anchor.variance_pct):.1f}% KPI Recovery",
                raci_owner=prop.get("raci_owner", "System"),
                approval_status=prop.get("approval_status", "PENDING_REVIEW"),
                source_layer=prop.get("source_layer", "Layer 3"),
                model_confidence_weight=0.95,
                critic_verdict=critique,
                requires_shadow_run=is_blue_sky
            )

        # Process main operational proposals
        for prop in all_proposals:
            action_block = process_proposal(prop, is_blue_sky=False)
            if action_block:
                recommended_actions_list.append(action_block)
                
        # If no valid actions, add a fallback
        if not recommended_actions_list:
            recommended_actions_list.append(RecommendedActionBlock(
                action_id="ACT-ERR-001", action="No valid actions passed security and threshold checks.", estimated_cost_usd=0.0, time_to_impact_minutes=0, expected_damage_reverted="0%", raci_owner="SYSTEM", approval_status="ERROR", source_layer="System", model_confidence_weight=0.0, critic_verdict="All proposals rejected.", requires_shadow_run=False
            ))

        financial_impact = float(context.get("financial_impact_usd", recommended_actions_list[0].estimated_cost_usd * 1.5))
        risk_level = "HIGH" if anchor.z_score >= 5.0 else "MEDIUM"

        exec_view = ExecutiveViewBlock(
            financial_impact_usd=financial_impact,
            business_risk_level=risk_level,
            recommended_actions=recommended_actions_list
        )

        # Make Engineer and Ops Views dynamic based on the actual driver and context
        raw_cause = primary_driver.content if not primary_driver.is_masked else primary_driver.title
        tech_root_cause = f"AI identified {raw_cause} via Swarm" """

p_code = re.sub(r'        # We wrap the single proposal into the views expected by Streamlit.*?tech_root_cause = f"AI identified \{raw_cause\} via \{approved_proposal\.get\(\'source_layer\', \'Swarm\'\)\}"', pipeline_replacement, p_code, flags=re.DOTALL)
p_code = p_code.replace('"master_payload": master_payload,', '"master_payload": master_payload,\n            "raw_state": final_state,')
with open(p_path, "w", encoding="utf-8") as f:
    f.write(p_code)

# 5. streamlit_app.py
s_path = r"D:\projects\Omnision\Omnision\kpi_engine\ui\streamlit_app.py"
with open(s_path, "r", encoding="utf-8") as f:
    s_code = f.read()

s_replacement = """        with col_ch2:
            st.markdown("### :material/lightbulb: Channel B: Blue-sky challenger solutions")
            
            blue_sky_proposals = result.get("raw_state", {}).get("blue_sky_proposals", [])
            blue_sky_critique = result.get("raw_state", {}).get("blue_sky_critique", "No critique generated.")
            
            if blue_sky_proposals:
                for idx, a in enumerate(blue_sky_proposals):
                    st.warning(f"**{a.get('action')}**\\n\\n〰️ Cost: `${float(a.get('estimated_cost_usd', 0)):,.2f}`\\n\\n〰️ Approval: `{a.get('approval_status')}`")
                    st.info(f"**The Reality Checker (Critic):** {blue_sky_critique}")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(":material/refresh: Rerun Blue-Sky", key=f"rerun_bs_{idx}"):
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
            else:
                st.info("No Blue-Sky actions generated.")

    # ==================== TAB 4: HUMAN RCA OVERRIDE SANDBOX ===================="""

s_code = re.sub(r'        with col_ch2:\n            st\.markdown\("### :material/lightbulb: Channel B: Blue-sky challenger solutions"\).*?# ==================== TAB 4: HUMAN RCA OVERRIDE SANDBOX ====================', s_replacement, s_code, flags=re.DOTALL)

with open(s_path, "w", encoding="utf-8") as f:
    f.write(s_code)

print("Patch applied successfully.")
