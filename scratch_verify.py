import json
from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.scoper.security_matrix import UserClearance

def main():
    engine = KPIStorytellingEngine()
    
    scenarios = [
        "SCENARIO_1_STRIPE_GATEWAY_OUTAGE",
        "SCENARIO_2_MULTIVARIATE_DAG_SHAP",
        "SCENARIO_3_COLD_START_PHASED_HANDOVER",
        "SCENARIO_4_SECURITY_CLEARANCE_MATRIX"
    ]
    
    personas = [
        ("EXECUTIVE_VP", UserClearance.EXECUTIVE_VP),
        ("SENIOR_ENGINEER", UserClearance.SENIOR_ENGINEER),
        ("JUNIOR_ANALYST", UserClearance.JUNIOR_ANALYST)
    ]
    
    print("========================================")
    print("OMNISION PROTOTYPE VERIFICATION MATRIX")
    print("========================================\n")
    
    for s_id in scenarios:
        print(f"--- BENCHMARK: {s_id} ---")
        
        for p_name, p_enum in personas:
            result = engine.run_pipeline(scenario_id=s_id, user_role=p_enum)
            status = result.get("status")
            
            if status == "ABSTAINED":
                print(f"[{p_name}] -> ABSTAINED: {result.get('reason')}")
            else:
                master = result.get("master_payload")
                if master:
                    driver = getattr(master.anchor_reference, "primary_driver", "Unknown")
                    exposure = getattr(master.executive_view, "financial_impact_usd", "Unknown")
                    risk = getattr(master.executive_view, "business_risk_level", "Unknown")
                    print(f"[{p_name}] -> SUCCESS | Driver: '{driver}' | Exposure: ${exposure} | Risk: {risk}")
                else:
                    print(f"[{p_name}] -> SUCCESS, but master_payload is missing.")
        print("\n")

if __name__ == '__main__':
    main()
