import re
file_path = r"D:\projects\Omnision\Omnision\kpi_engine\pipeline.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """        tokens = final_state.get("tokens_consumed", 0)
        cost_usd = round((tokens / 1000.0) * self.config.cost_per_1k_input_tokens_usd, 4)"""
replacement = """        tokens = final_state.get("tokens_consumed", 0)
        self.supervisor.cumulative_token_spend += tokens
        cost_usd = round((tokens / 1000.0) * self.config.cost_per_1k_input_tokens_usd, 4)"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added cumulative token tracking")
else:
    print("Target not found")
