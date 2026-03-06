"""
Full 6-layer Supply Chain Agent pipeline with human review gates.
Runs on mock data by default (USE_MOCK_DATA=1). No real API or live data required.
Orchestrates: Perception (+ supplier health) -> Risk Intelligence -> Planning (Mohid + Tamim) -> Action -> Memory -> Transparency.
"""

import argparse
import json
import os
import sys
import uuid
from perception.news_parser import NewsParser
from perception.erp_mock import ERPMockConnector
from perception.classifier import RiskClassifier
from perception.supplier_health import compute_supplier_health_scores, format_supplier_health_for_summary
from perception.models import SupplyRiskAssessment
from risk_intelligence.adapter import to_perception_output, get_manufacturer_profile
from risk_intelligence.risk_engine import assess_risk
from risk_intelligence.planning_engine import simulate_plan_options
from action.action_generator import generate_actions
from memory.reflection import ReflectionEngine
from transparency.transparency import build_transparency
from schemas.tamim_schema import (
    PerceptionOutput,
    ManufacturerProfile,
    RiskAssessmentResponse,
    PlanningResponse,
    PlanOption,
    ActionRequest,
    TransparencyRequest,
)
from planning.decision_engine import DecisionEngine
from planning.models import MitigationPlan, ScenarioSimulation


def _prompt(no_input: bool, message: str, default: str = "y") -> str:
    if no_input:
        return default
    return input(message).strip().lower() or default


def _mitigation_plan_to_planning_response(plan: MitigationPlan) -> PlanningResponse:
    """Build Tamim PlanningResponse from Mohid MitigationPlan for Layer 4 and Layer 6."""
    opt = PlanOption(
        name=plan.chosen_scenario.action_type,
        mitigation_cost=float(plan.chosen_scenario.estimated_cost_usd),
        resulting_downtime_days=0,
        revenue_saved=0,
        penalty_saved=0,
        net_benefit=0,
    )
    return PlanningResponse(options=[opt], recommended_option=plan.chosen_scenario.action_type)


def run_full_pipeline(iterations: int = 2, no_input: bool = False):
    # Ensure mock mode from env (default 1) is used by config
    if "USE_MOCK_DATA" not in os.environ:
        os.environ["USE_MOCK_DATA"] = "1"
    import config as _config  # noqa: F401

    print("Initializing 6-Layer Supply Chain Agent (mock data only)...")
    news_parser = NewsParser()
    erp = ERPMockConnector()
    classifier = RiskClassifier()
    planner = DecisionEngine()
    memory = ReflectionEngine()

    for i in range(iterations):
        print(f"\n{'='*60}\n--- Cycle {i+1} ---\n{'='*60}")

        # ---------- Layer 1: Perception + Supplier health ----------
        news_signal = news_parser.fetch_latest_news()
        print(f"[Layer 1] News: {news_signal.headline}")
        location_keyword = (news_signal.location or "").split(",")[0].strip() or ""
        erp_context = erp.get_parts_by_location(location_keyword) if location_keyword else erp.get_inventory_snapshot()
        print(f"[Layer 1] ERP context: {len(erp_context)} parts.")

        supplier_health = compute_supplier_health_scores(erp_context)
        print(f"[Layer 1] Supplier health: {format_supplier_health_for_summary(supplier_health)}")

        assessment = classifier.assess_risk(news_signal, erp_context)
        if not assessment:
            print("[Error] Layer 1 failed to produce assessment.")
            continue

        print("\n*** LAYER 1 – SUMMARY ***")
        print(json.dumps(assessment.model_dump(), indent=2))
        print(f"\n[Human Review 1] Summary: {assessment.news_summary}")
        r1 = _prompt(no_input, "Approve summary and send to Risk Intelligence (Layer 2)? (y/n/skip): ")
        if r1 == "skip":
            print("[Human Override] Skipping event.")
            continue
        if r1 != "y":
            print("[Human Override] Rejected.")
            continue

        # ---------- Adapter + Layer 2: Risk Intelligence ----------
        perception_output = to_perception_output(assessment, news_signal, erp_context)
        manufacturer_profile = get_manufacturer_profile(erp_context)
        risk_result = assess_risk(perception_output.model_dump(), manufacturer_profile.model_dump())

        print("\n*** LAYER 2 – RISK INTELLIGENCE ***")
        print(json.dumps(risk_result.model_dump(), indent=2))
        print(f"\n[Human Review 2] Risk level: {risk_result.risk_level}. Revenue at risk: ${risk_result.revenue_at_risk:,.0f}")
        r2 = _prompt(no_input, "Approve and send to Planning (Layer 3)? (y/n/skip): ")
        if r2 == "skip":
            print("[Human Override] Skipping event.")
            continue
        if r2 != "y":
            print("[Human Override] Rejected.")
            continue

        # ---------- Layer 3: Planning – Mohid (with real Layer 2 data) + Tamim options ----------
        mohid_plan = planner.formulate_plan(assessment, layer2_risk_data=risk_result)
        tamim_response = simulate_plan_options(risk_result)
        print("\n*** LAYER 3 – PLANNING (Mohid + Tamim) ***")
        print("Tamim options:")
        for opt in tamim_response.options:
            print(f"  - {opt.name}: cost ${opt.mitigation_cost:,.0f}, net benefit ${opt.net_benefit:,.0f}")
        print(f"Mohid chosen plan: {mohid_plan.chosen_scenario.action_type} (cost ${mohid_plan.chosen_scenario.estimated_cost_usd:,})")
        print(f"Reasoning: {mohid_plan.reasoning_tree}")
        print(f"\n[Human Review 3] Approve Mohid plan and send to Action layer (Layer 4)?")
        r3 = _prompt(no_input, "Approve? (y/n/skip): ")
        if r3 == "skip":
            print("[Human Override] Skipping event.")
            continue
        if r3 != "y":
            print("[Human Override] Rejected.")
            continue

        planning_response = _mitigation_plan_to_planning_response(mohid_plan)

        # ---------- Layer 4: Autonomous Action ----------
        action_request = ActionRequest(
            manufacturer_profile=manufacturer_profile,
            risk_assessment=risk_result,
            planning_response=planning_response,
        )
        actions = generate_actions(action_request)
        print("\n*** LAYER 4 – ACTIONS ***")
        print("Supplier email:\n", actions.supplier_email)
        print("\nExecutive alert:\n", actions.executive_alert)
        print("\nPO adjustment:\n", actions.po_adjustment_suggestion)
        if actions.escalation_trigger:
            print("\nEscalation:", actions.escalation_trigger)
        for line in actions.workflow_integration_log:
            print(" ", line)
        print("\n[Human Review 4] Execute these actions?")
        r4 = _prompt(no_input, "Execute plan? (y/n): ")
        if r4 == "y":
            _execute_actions(actions, risk_result)
            print("[System] Plan executed (logged to pending_actions.json).")
        else:
            print("[System] Execution cancelled.")

        # ---------- Layer 5: Memory & Reflection ----------
        print("\n[Layer 5] Passing to Memory & Reflection...")
        memory.reflect_and_store(assessment, mohid_plan, auto_save=no_input)

        # ---------- Layer 6: Decision Transparency ----------
        transparency_request = TransparencyRequest(
            perception_output=perception_output,
            risk_assessment=risk_result,
            planning_response=planning_response,
        )
        transparency = build_transparency(transparency_request)
        print("\n*** LAYER 6 – DECISION TRANSPARENCY (FINAL SUMMARY) ***")
        print("Reasoning trace:", transparency.reasoning_trace)
        print("Human override threshold:", transparency.human_override_threshold)
        print("Assumptions:", transparency.assumptions)
        print("Bias and constraint validation:", transparency.bias_and_constraint_validation)
        print("\n" + "="*60 + " Cycle complete.\n")

    print("Pipeline finished.")


def _execute_actions(actions, risk_assessment: RiskAssessmentResponse):
    """Log executed actions to pending_actions.json (mock workflow)."""
    path = os.path.join(os.path.dirname(__file__), "pending_actions.json")
    record = {
        "executive_alert": actions.executive_alert,
        "po_adjustment_suggestion": actions.po_adjustment_suggestion,
        "risk_level": risk_assessment.risk_level,
        "affected_part": risk_assessment.affected_part,
        "escalation_trigger": getattr(actions, "escalation_trigger", "") or "",
    }
    history = []
    if os.path.exists(path):
        with open(path, "r") as f:
            history = json.load(f)
    history.append(record)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 6-layer Supply Chain Agent (mock data by default)")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock data only (default: True)")
    parser.add_argument("--no-mock", action="store_false", dest="mock", help="Allow live API (e.g. Gemini) when key is set")
    parser.add_argument("--iterations", type=int, default=2, help="Number of news cycles (default: 2)")
    parser.add_argument("--no-input", action="store_true", help="Non-interactive: auto-approve all steps (for CI/demo)")
    args = parser.parse_args()
    os.environ["USE_MOCK_DATA"] = "1" if args.mock else "0"
    run_full_pipeline(iterations=args.iterations, no_input=args.no_input)
