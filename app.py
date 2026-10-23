"""
Root entry point for the Omnision dashboard.

    streamlit run app.py

Streamlit re-executes this file on every interaction, so the dashboard script is executed with
runpy each time (a plain import would only render once per process).
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "kpi_engine" / "ui" / "streamlit_app.py"), run_name="__main__")
