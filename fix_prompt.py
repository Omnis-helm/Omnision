import re
file_path = r"D:\projects\Omnision\Omnision\kpi_engine\suggester\llm_swarm.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'f"Required keys: action, source_layer, estimated_cost_usd, time_to_impact_minutes, raci_owner, approval_status.\\n"',
    'f"Required keys: action, source_layer, estimated_cost_usd, time_to_impact_minutes, raci_owner, approval_status, operational_lever_required.\\n"'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated LLM prompt with operational_lever_required")
