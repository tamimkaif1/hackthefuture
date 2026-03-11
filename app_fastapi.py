"""
FastAPI entry point for Supply Chain Agent API and frontend.
- Serves the web UI at / (static/index.html) and /static/*
- Exposes Tamim endpoints: /risk-assessment, /plan, /actions, /transparency
- Exposes wizard endpoints for the frontend: /api/step1_perception ... /api/step6_transparency
"""

import json
from pathlib import Path

import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from schemas.tamim_schema import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    PlanningResponse,
    PlanOption,
    ActionRequest,
    ActionResponse,
    TransparencyRequest,
    TransparencyResponse,
    ManufacturerProfile,
    PerceptionOutput,
)
from risk_intelligence.risk_engine import assess_risk
from risk_intelligence.planning_engine import simulate_plan_options
from risk_intelligence.adapter import to_perception_output, get_manufacturer_profile
from action.action_generator import generate_actions
from transparency.transparency import build_transparency
from perception.news_parser import NewsParser
from perception.erp_mock import ERPMockConnector
from perception.classifier import RiskClassifier
from perception.supplier_health import compute_supplier_health_scores, format_supplier_health_for_summary
from perception.models import SupplyRiskAssessment
from planning.decision_engine import DecisionEngine
from planning.models import MitigationPlan
from memory.reflection import ReflectionEngine
from gemini_service import get_gemini_chat, is_live_mode

app = FastAPI(title="Supply Chain Resilience Agent API")

# Paths for static files (run from project root)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def _mitigation_plan_to_planning_response(plan: MitigationPlan) -> PlanningResponse:
    """Build Tamim PlanningResponse from Mohid MitigationPlan."""
    opt = PlanOption(
        name=plan.chosen_scenario.action_type,
        mitigation_cost=float(plan.chosen_scenario.estimated_cost_usd),
        resulting_downtime_days=0,
        revenue_saved=0,
        penalty_saved=0,
        net_benefit=0,
    )
    return PlanningResponse(options=[opt], recommended_option=plan.chosen_scenario.action_type)


def _execute_actions(actions: ActionResponse, risk_assessment: dict):
    """Log executed actions to pending_actions.json (mock workflow)."""
    path = BASE_DIR / "pending_actions.json"
    record = {
        "executive_alert": actions.executive_alert,
        "po_adjustment_suggestion": actions.po_adjustment_suggestion,
        "risk_level": risk_assessment.get("risk_level", ""),
        "affected_part": risk_assessment.get("affected_part", ""),
        "escalation_trigger": getattr(actions, "escalation_trigger", "") or "",
    }
    history = []
    if path.exists():
        try:
            with open(path, "r") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
        except json.JSONDecodeError:
            # If the file is empty or corrupted, reset the history.
            history = []
    history.append(record)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


# ----- Frontend: serve static and index -----
@app.get("/")
def serve_index():
    """Serve the single-page frontend."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return {"message": "Supply Chain Resilience Agent API is running.", "frontend": "static/index.html not found"}
    return FileResponse(index_path)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ----- Wizard API (used by the frontend) -----
@app.get("/api/step1_perception")
def api_step1_perception():
    """Layer 1: Perception + supplier health. Returns assessment, perception_output, manufacturer_profile, and display fields."""
    news_parser = NewsParser()
    erp = ERPMockConnector()
    classifier = RiskClassifier()
    news_signal = news_parser.fetch_latest_news()
    location_keyword = (news_signal.location or "").split(",")[0].strip() or ""
    erp_context = erp.get_parts_by_location(location_keyword) if location_keyword else erp.get_inventory_snapshot()
    supplier_health = compute_supplier_health_scores(erp_context)
    supplier_health_summary = format_supplier_health_for_summary(supplier_health)
    assessment = classifier.assess_risk(news_signal, erp_context)
    if not assessment:
        raise HTTPException(status_code=500, detail="Layer 1 failed to produce assessment")
    perception_output = to_perception_output(assessment, news_signal, erp_context)
    manufacturer_profile = get_manufacturer_profile(erp_context)
    return {
        "assessment": assessment.model_dump(),
        "perception_output": perception_output.model_dump(),
        "manufacturer_profile": manufacturer_profile.model_dump(),
        "news_headline": news_signal.headline,
        "erp_context_size": len(erp_context),
        "supplier_health_summary": supplier_health_summary,
    }


@app.get("/api/step1_all_risks")
def api_step1_all_risks():
    """Layer 1: Classify ALL mock news signals and return as an array for bubble visualization."""
    news_parser = NewsParser()
    erp = ERPMockConnector()
    classifier = RiskClassifier()
    all_signals = news_parser.fetch_all_news()
    results = []
    for news_signal in all_signals:
        location_keyword = (news_signal.location or "").split(",")[0].strip() or ""
        erp_context = erp.get_parts_by_location(location_keyword) if location_keyword else erp.get_inventory_snapshot()
        supplier_health = compute_supplier_health_scores(erp_context)
        supplier_health_summary = format_supplier_health_for_summary(supplier_health)
        assessment = classifier.assess_risk(news_signal, erp_context)
        if not assessment:
            continue
        perception_output = to_perception_output(assessment, news_signal, erp_context)
        manufacturer_profile = get_manufacturer_profile(erp_context)
        results.append({
            "assessment": assessment.model_dump(),
            "perception_output": perception_output.model_dump(),
            "manufacturer_profile": manufacturer_profile.model_dump(),
            "news_headline": news_signal.headline,
            "news_content": news_signal.content,
            "news_source": news_signal.source,
            "news_location": news_signal.location or "",
            "erp_context_size": len(erp_context),
            "supplier_health_summary": supplier_health_summary,
        })
    return {"risks": results}



@app.post("/api/step1_customize")
def api_step1_customize(payload: dict):
    """Layer 1: Revise assessment based on user's custom prompt."""
    assessment_dict = payload["assessment"].copy()
    custom = (payload.get("custom_prompt") or "").strip()
    if custom:
        assessment_dict["rationale"] = (
            f"[User override: {custom}] " + assessment_dict.get("rationale", "")
        )
    return {"assessment": assessment_dict}


@app.post("/api/step2_risk")
def api_step2_risk(payload: dict):
    """Layer 2: Risk assessment from perception + manufacturer profile."""
    result = assess_risk(
        payload["perception_output"],
        payload["manufacturer_profile"],
    )
    out = result.model_dump()
    custom = (payload.get("custom_prompt") or "").strip()
    if custom:
        out["_user_note"] = custom
    return out


@app.post("/api/step3_plan")
def api_step3_plan(payload: dict):
    """Layer 3: Mohid plan + Tamim options. Returns mohid_plan, planning_response, tamim_options."""
    assessment_dict = payload["assessment"]
    risk_assessment = payload.get("risk_assessment") or {}
    custom_prompt = (payload.get("custom_prompt") or "").strip() or None
    assessment = SupplyRiskAssessment(**assessment_dict)
    planner = DecisionEngine()
    mohid_plan = planner.formulate_plan(assessment, layer2_risk_data=risk_assessment or None, custom_prompt=custom_prompt)

    # Build a fallback RiskAssessmentResponse if step 2 was skipped or risk_assessment is null
    if not risk_assessment:
        score = assessment_dict.get("risk_score", 7)
        risk_assessment = {
            "event_type": assessment_dict.get("signal_id", "unknown"),
            "affected_part": (assessment_dict.get("affected_parts") or ["unknown"])[0]
                if isinstance(assessment_dict.get("affected_parts"), list)
                else str(assessment_dict.get("affected_parts", "unknown")),
            "disruption_probability": 0.85,
            "delay_days": 30,
            "inventory_days": 30,
            "downtime_days": max(0, 30 - 30),
            "revenue_at_risk": score * 500_000,
            "sla_penalty_risk": score * 100_000,
            "total_financial_exposure": score * 600_000,
            "risk_level": "high" if score >= 7 else "medium",
        }

    risk_response = RiskAssessmentResponse(**risk_assessment)
    tamim_response = simulate_plan_options(risk_response)
    planning_response = _mitigation_plan_to_planning_response(mohid_plan)
    return {
        "mohid_plan": mohid_plan.model_dump(),
        "planning_response": planning_response.model_dump(),
        "tamim_options": [o.model_dump() for o in tamim_response.options],
    }



@app.post("/api/step4_actions_generate")
def api_step4_actions_generate(payload: dict):
    """Layer 4: Generate actions from manufacturer_profile, risk_assessment, planning_response."""
    # Guard: risk_assessment may be null if step 2 was skipped
    raw_risk = payload.get("risk_assessment") or {
        "event_type": "shipping_delay", "affected_part": "MECH-VALVE-202",
        "disruption_probability": 0.85, "delay_days": 30, "inventory_days": 30,
        "downtime_days": 0, "revenue_at_risk": 5_000_000,
        "sla_penalty_risk": 1_000_000, "total_financial_exposure": 6_000_000,
        "risk_level": "high",
    }

    # Guard: planning_response may be partial (missing 'options' list)
    raw_plan = payload.get("planning_response") or {}
    if "options" not in raw_plan or not raw_plan["options"]:
        raw_plan["options"] = [{
            "name": raw_plan.get("recommended_option", "Expedite alternate freight"),
            "mitigation_cost": raw_plan.get("expected_cost_usd", 500_000),
            "resulting_downtime_days": 0,
            "revenue_saved": 4_000_000,
            "penalty_saved": 800_000,
            "net_benefit": 4_300_000,
        }]
    if "recommended_option" not in raw_plan:
        raw_plan["recommended_option"] = raw_plan["options"][0]["name"]

    req = ActionRequest(
        manufacturer_profile=ManufacturerProfile(**payload["manufacturer_profile"]),
        risk_assessment=RiskAssessmentResponse(**raw_risk),
        planning_response=PlanningResponse(**raw_plan),
    )
    actions = generate_actions(req)
    out = actions.model_dump()
    custom = (payload.get("custom_prompt") or "").strip()
    if custom:
        prefix = f"[Per user request: {custom}]\n\n"
        out["supplier_email"] = prefix + out.get("supplier_email", "")
        out["executive_alert"] = prefix + out.get("executive_alert", "")
        out["po_adjustment_suggestion"] = prefix + out.get("po_adjustment_suggestion", "")
    return out



@app.post("/api/step4_actions_execute")
def api_step4_actions_execute(payload: dict):
    """Layer 4: Execute actions (log to pending_actions.json)."""
    actions = ActionResponse(**payload["actions"])
    _execute_actions(actions, payload["risk_assessment"])
    return {"status": "ok"}


@app.post("/api/step5_memory")
def api_step5_memory(payload: dict):
    """Layer 5: Memory & reflection (save to past_disruptions + memory_chunks). Returns reflection for UI."""
    assessment = SupplyRiskAssessment(**payload["assessment"])
    mohid_plan = MitigationPlan(**payload["mohid_plan"])
    custom = (payload.get("custom_prompt") or "").strip()
    memory = ReflectionEngine()
    reflection = memory.reflect_and_store(assessment, mohid_plan, auto_save=True)
    resilience_score = mohid_plan.chosen_scenario.resilience_score
    success_metric = (
        f"Mitigation executed successfully. Resilience score: {resilience_score}/10. "
        f"Action: {mohid_plan.chosen_scenario.action_type} (${mohid_plan.chosen_scenario.estimated_cost_usd:,} cost)."
    )
    summary = reflection.summary_text
    takeaways = reflection.key_takeaways
    if custom:
        summary = f"[User directive: {custom}]\n\n{summary}"
        takeaways = f"[User directive: {custom}]\n\n{takeaways}"
    return {
        "status": "ok",
        "summary_text": summary,
        "key_takeaways": takeaways,
        "success_metric": success_metric,
    }


@app.post("/api/step6_transparency")
def api_step6_transparency(payload: dict):
    """Layer 6: Transparency report."""
    req = TransparencyRequest(
        perception_output=PerceptionOutput(**payload["perception_output"]),
        risk_assessment=RiskAssessmentResponse(**payload["risk_assessment"]),
        planning_response=PlanningResponse(**payload["planning_response"]),
    )
    result = build_transparency(req)
    out = result.model_dump()
    custom = (payload.get("custom_prompt") or "").strip()
    if custom:
        out["reasoning_trace"] = f"[User override: {custom}]\n\n{out.get('reasoning_trace', '')}"
        out["assumptions"] = [f"User directive incorporated: {custom}"] + out.get("assumptions", [])
    return out


# ----- Raw Tamim API (programmatic) -----
@app.get("/health")
def health():
    return {
        "message": "Supply Chain Resilience Agent API is running.",
        "gemini_live_mode": is_live_mode(),
    }


@app.get("/debug/gemini")
def debug_gemini():
    """
    Simple debug endpoint to verify that Gemini is reachable.

    Returns a short AI-generated message plus the model name.
    """
    try:
        logging.info("[Debug] Calling Gemini from /debug/gemini endpoint...")
        llm = get_gemini_chat()
        response = llm.invoke(
            "You are part of a supply chain risk demo. "
            "Respond with a single short sentence confirming that Gemini is live."
        )
        return {
            "status": "ok",
            "model": getattr(llm, "model", "unknown"),
            "message": response.content,
        }
    except Exception as e:
        logging.exception("Gemini debug call failed")
        return {
            "status": "error",
            "error": str(e),
            "message": "AI analysis is unavailable. Check GOOGLE_API_KEY and network connectivity.",
        }


@app.post("/risk-assessment", response_model=RiskAssessmentResponse)
def risk_assessment(payload: RiskAssessmentRequest):
    result = assess_risk(
        payload.perception_output.model_dump(),
        payload.manufacturer_profile.model_dump(),
    )
    return result


@app.post("/plan", response_model=PlanningResponse)
def plan(payload: RiskAssessmentRequest):
    risk = assess_risk(
        payload.perception_output.model_dump(),
        payload.manufacturer_profile.model_dump(),
    )
    return simulate_plan_options(risk)


@app.post("/actions", response_model=ActionResponse)
def actions(payload: ActionRequest):
    return generate_actions(payload)


@app.post("/transparency", response_model=TransparencyResponse)
def transparency(payload: TransparencyRequest):
    return build_transparency(payload)
