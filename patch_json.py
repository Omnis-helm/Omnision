import os
import re

path = r"D:\projects\Omnision\Omnision\kpi_engine\suggester\llm_swarm.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

target = """            try:
                content = str(response.content).strip()
                
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx+1]
                    
                proposal = json.loads(content)"""

replacement = """            try:
                content = str(response.content).strip()
                
                # Force strip markdown JSON block wrappers
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx+1]
                    
                proposal = json.loads(content)"""

code = code.replace(target, replacement)
with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Applied JSON stripping to llm_swarm.py")
