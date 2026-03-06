"""
Optional FastAPI entry point for Supply Chain Agent API.
Exposes Tamim's endpoints: /risk-assessment, /plan, /actions, /transparency.
"""

from fastapi import FastAPI
from schemas.tamim_schema import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    PlanningResponse,
    ActionRequest,
    ActionResponse,
    TransparencyRequest,
    TransparencyResponse,
)
from risk_intelligence.risk_engine import assess_risk
from risk_intelligence.planning_engine import simulate_plan_options
from action.action_generator import generate_actions
from transparency.transparency import build_transparency

app = FastAPI(title="Supply Chain Resilience Agent API")


@app.get("/")
def root():
    return {"message": "Supply Chain Resilience Agent API is running."}


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
