"""Pydantic models for Tamim's risk, planning, action, and transparency layers."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class PerceptionOutput(BaseModel):
    event_type: str
    affected_region: str
    confidence: float = Field(ge=0.0, le=1.0)
    affected_suppliers: List[str]
    affected_parts: List[str]
    delay_days_estimate: int = Field(ge=0)


class ManufacturerProfile(BaseModel):
    company_name: str
    revenue_per_day: float = Field(ge=0)
    inventory_days: Dict[str, int]
    sla_penalty_per_day: float = Field(ge=0)
    critical_parts: List[str]


class RiskAssessmentRequest(BaseModel):
    perception_output: PerceptionOutput
    manufacturer_profile: ManufacturerProfile


class RiskAssessmentResponse(BaseModel):
    event_type: str
    affected_part: str
    disruption_probability: float
    delay_days: int
    inventory_days: int
    downtime_days: int
    revenue_at_risk: float
    sla_penalty_risk: float
    total_financial_exposure: float
    risk_level: str


class PlanOption(BaseModel):
    name: str
    mitigation_cost: float
    resulting_downtime_days: int
    revenue_saved: float
    penalty_saved: float
    net_benefit: float


class PlanningResponse(BaseModel):
    options: List[PlanOption]
    recommended_option: str


class ActionRequest(BaseModel):
    manufacturer_profile: ManufacturerProfile
    risk_assessment: RiskAssessmentResponse
    planning_response: PlanningResponse


class ActionResponse(BaseModel):
    supplier_email: str
    executive_alert: str
    po_adjustment_suggestion: str
    escalation_trigger: str = ""
    workflow_integration_log: List[str] = Field(default_factory=list)


class TransparencyRequest(BaseModel):
    perception_output: PerceptionOutput
    risk_assessment: RiskAssessmentResponse
    planning_response: PlanningResponse


class TransparencyResponse(BaseModel):
    reasoning_trace: str
    human_override_threshold: str
    assumptions: List[str]
    bias_and_constraint_validation: List[str] = Field(default_factory=list)
