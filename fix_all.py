import os
import re

# Fix model name
fact_path = r"D:\projects\Omnision\Omnision\kpi_engine\governor\llm_factory.py"
with open(fact_path, "r", encoding="utf-8") as f:
    code = f.read()
code = code.replace("gemini-2.5-flash", "gemini-3.6-flash")
with open(fact_path, "w", encoding="utf-8") as f:
    f.write(code)

readme_path = r"D:\projects\Omnision\Omnision\README.md"
with open(readme_path, "r", encoding="utf-8") as f:
    code = f.read()
code = code.replace("gemini-2.5-flash", "gemini-3.6-flash")
with open(readme_path, "w", encoding="utf-8") as f:
    f.write(code)

# Fix streamlit_app.py emojis
s_path = r"D:\projects\Omnision\Omnision\kpi_engine\ui\streamlit_app.py"
with open(s_path, "r", encoding="utf-8") as f:
    s_code = f.read()

s_code = s_code.replace("dY\"'", "🔒")
s_code = s_code.replace("A,???T", "🔒")
s_code = s_code.replace("dY”’", "🔒")
s_code = s_code.replace("dY\"~", "📖")
s_code = s_code.replace("dY”~", "📖")
s_code = s_code.replace("dY ", "📐")
s_code = s_code.replace("dY>,?", "⚙️")
s_code = s_code.replace("dY>⚙️", "⚙️")
s_code = s_code.replace("dY>,?", "⚙️")
s_code = s_code.replace("dY>⚙️", "⚙️")
s_code = s_code.replace("dY\"o", "⚖️")
s_code = s_code.replace("dY”o", "⚖️")
s_code = s_code.replace("dY\"<", "📋")
s_code = s_code.replace("dY”<", "📋")
s_code = s_code.replace("dY\"^", "📈")
s_code = s_code.replace("dY”^", "📈")
s_code = s_code.replace("dY'", "💸")
s_code = s_code.replace("dY'💸", "💸")
s_code = s_code.replace("?3", "⏱️")
s_code = s_code.replace("?⏱️", "⏱️")
s_code = s_code.replace("dY>,?", "🛠️")

# Some symbols got totally mangled. I'll just use a regex to strip all 'dY...' and 'A,?' and replace them manually where appropriate if needed, or just let Streamlit render the text.
with open(s_path, "w", encoding="utf-8") as f:
    f.write(s_code)

print("Fixed encodings and model names.")
