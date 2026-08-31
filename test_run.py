import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.config import CONFIG

try:
    print("Initializing Engine...")
    engine = KPIStorytellingEngine()
    
    print("Running Pipeline...")
    res1 = engine.run_pipeline(force_refresh=True)
    print("Pipeline Success. Payload keys:", res1.keys())
    
    surviving_nodes = res1.get("surviving_evidence", [])
    if surviving_nodes:
        print("Testing RCA Override...")
        res2 = engine.handle_human_rca_override(
            scenario_id="SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
            demoted_node_id=surviving_nodes[0].node_id,
            custom_injected_text="Testing custom injection"
        )
        print("Override Success. Result keys:", res2.keys())
        
        print("Testing Reject Fix...")
        res3 = engine.handle_rejected_fix(
            scenario_id="SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
            primary_driver=surviving_nodes[0],
            rejected_action_text="Test rejected action"
        )
        print("Reject Fix Success. Result keys:", res3.keys())
        
    print("All tests passed.")
except Exception as e:
    import traceback
    traceback.print_exc()
