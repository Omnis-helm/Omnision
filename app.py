"""
Root Entry Point for Streamlit Dashboard
You can run this directly with: streamlit run app.py
"""

import sys
import os
from pathlib import Path

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import runpy

# Execute the main dashboard script properly on every rerun
runpy.run_path(str(ROOT_DIR / "kpi_engine" / "ui" / "streamlit_app.py"), run_name="__main__")
