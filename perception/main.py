import time
import json
from perception.news_parser import NewsParser
from perception.erp_mock import ERPMockConnector
from perception.classifier import RiskClassifier
from planning.decision_engine import DecisionEngine
from memory.reflection import ReflectionEngine

def run_perception_loop(iterations=2):
    print("Initializing Supply Chain Perception & Execution Agent (Mohid's Modules)...")
    news_parser = NewsParser()
    erp = ERPMockConnector()
    classifier = RiskClassifier()
    planner = DecisionEngine()
    memory = ReflectionEngine()
    
    print("\nStarting Agent Loop...")
    for i in range(iterations):
        print(f"\n--- Cycle {i+1} ---")
        
        # 1. Ingest
        news_signal = news_parser.fetch_latest_news()
        print(f"[News Ingest] Received: {news_signal.headline}")
        
        # 2. Contextualize (Get ERP data based on news location or entities)
        # In a real app, you'd do NLP entity extraction first, but we will match on location string
        location_keyword = news_signal.location.split(",")[0] if news_signal.location else ""
        erp_context = erp.get_parts_by_location(location_keyword)
        
        print(f"[ERP Context] Found {len(erp_context)} affected parts in inventory.")
        
        # 3. Classify & Assess
        assessment = classifier.assess_risk(news_signal, erp_context)
        
        if assessment:
            print("\n*** RISK ASSESSMENT RESULT ***")
            # Print as beautiful JSON
            print(json.dumps(assessment.model_dump(), indent=2))
            
            print(f"\n[ACTION REQUIRED] AI Summary: {assessment.news_summary}")
            review = input("Approve summary and send to Planning Engine (since Tamim's Layer 2 is mocked)? (y/n/skip): ")
            
            if review.lower() == 'skip':
                 print("[Human Override] Skipping event.")
                 continue
            elif review.lower() != 'y':
                print("[Human Override] Event rejected.")
                continue
                
            print("[System] Authorized. Passing to Layer 3 (Planning)...")
            
            # --- LAYER 3: PLANNING & DECISION ENGINE ---
            plan = planner.formulate_plan(assessment)
            print("\n*** MITIGATION PLAN FORMULATED ***")
            print(json.dumps(plan.model_dump(), indent=2))
            
            print(f"\n[ACTION REQUIRED] AI Recommendation: {plan.chosen_scenario.action_type} - Costs ${plan.chosen_scenario.estimated_cost_usd}")
            print(f"Reasoning: {plan.reasoning_tree}")
            
            plan_review = input("Execute chosen mitigation plan via Layer 4 (Tamim's Action Layer)? (y/n): ")
            if plan_review.lower() == 'y':
                print("[System] Action executed.")
                
            # --- LAYER 5: MEMORY & REFLECTION ---
            print("\n[System] Passing execution record to Memory & Reflection...")
            memory.reflect_and_store(assessment, plan)
            
        else:
            print("[Error] Failed to generate assessment.")
            
        time.sleep(1) # Small pause between cycles

if __name__ == "__main__":
    run_perception_loop(iterations=2)
