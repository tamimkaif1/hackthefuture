import uuid
import json
from typing import Optional, Any
from perception.models import SupplyRiskAssessment
from planning.models import MitigationPlan, ScenarioSimulation

try:
    from langchain_core.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    _LANGCHAIN_AVAILABLE = True
except Exception:
    _LANGCHAIN_AVAILABLE = False


def _mock_plan_from_layer2(
    risk_assessment: SupplyRiskAssessment,
    layer2_risk: Optional[Any],
    custom_prompt: Optional[str] = None,
) -> MitigationPlan:
    """Deterministic mock plan from Layer 1 + Layer 2 data (no API). custom_prompt influences choice."""
    part = risk_assessment.affected_parts[0] if risk_assessment.affected_parts else "Unknown"
    # Use Layer 2 numbers if provided
    if layer2_risk is not None:
        exposure = getattr(layer2_risk, "total_financial_exposure", None) or (layer2_risk.get("total_financial_exposure") if isinstance(layer2_risk, dict) else 0)
        downtime = getattr(layer2_risk, "downtime_days", None) or (layer2_risk.get("downtime_days") if isinstance(layer2_risk, dict) else 12)
    else:
        exposure = 2_500_000
        downtime = 12

    # User override: keyword matching on custom_prompt
    prompt_lower = (custom_prompt or "").lower()
    action_type = None
    cost = None
    realloc = None
    buffer = None
    if prompt_lower:
        if any(w in prompt_lower for w in ["cheapest", "low cost", "buffer", "stock", "minimize cost"]):
            action_type, cost, realloc, buffer = "Increase emergency buffer stock", 80000, "N/A", 500
        elif any(w in prompt_lower for w in ["air", "fast", "expedite", "urgent", "speed"]):
            action_type, cost, realloc, buffer = "Air freight critical components", 350000, "Alternate supplier", 2000
        elif any(w in prompt_lower for w in ["supplier", "alternate", "switch", "re-source"]):
            action_type, cost, realloc, buffer = "Switch partial volume to alternate supplier", 150000, "Alternate supplier", 1000
        elif any(w in prompt_lower for w in ["nothing", "do nothing", "wait"]):
            action_type, cost, realloc, buffer = "Do nothing", 0, "N/A", 0

    # Fallback: exposure-based default
    if action_type is None:
        if exposure >= 5_000_000:
            action_type, cost, realloc, buffer = "Air freight critical components", 350000, "Alternate supplier", 2000
        elif exposure >= 1_000_000:
            action_type, cost, realloc, buffer = "Switch partial volume to alternate supplier", 150000, "Alternate supplier", 1000
        else:
            action_type, cost, realloc, buffer = "Increase emergency buffer stock", 80000, "N/A", 500

    if action_type == "Do nothing":
        svc_impact = f"No mitigation; baseline downtime {downtime} days"
        res_score = 2
    else:
        svc_impact = f"Downtime reduced (mock); was {downtime} days"
        res_score = min(10, max(1, 10 - (downtime // 3)))

    return MitigationPlan(
        plan_id=str(uuid.uuid4()),
        chosen_scenario=ScenarioSimulation(
            scenario_id="mock-plan",
            action_type=action_type,
            estimated_cost_usd=cost,
            service_level_impact=svc_impact,
            resilience_score=res_score,
        ),
        supplier_reallocation_target=realloc,
        buffer_stock_adjustment=buffer,
        reasoning_tree=f"Mock: Chose {action_type} based on financial exposure ${exposure:,.0f} and downtime {downtime} days."
        + (f" [User directive: {custom_prompt[:100]}...]" if custom_prompt and len(custom_prompt) > 100 else (f" [User directive: {custom_prompt}]" if custom_prompt else "")),
    )


class DecisionEngine:
    def __init__(self, use_mock: bool = None):
        self.use_mock = use_mock
        if self.use_mock is None:
            try:
                self.use_mock = __import__("config", fromlist=["USE_MOCK_DATA"]).USE_MOCK_DATA
            except Exception:
                self.use_mock = True
        self.llm = None
        self.prompt = None
        if not self.use_mock and _LANGCHAIN_AVAILABLE:
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-fast", temperature=0.3)
            self.prompt = PromptTemplate(
                input_variables=["risk_assessment", "layer2_mock_data"],
                template="""
                You are the Planning & Decision Engine of a Supply Chain Resilience AI.
                You have received a validated Risk Assessment from Layer 1, and deep impact metrics from Layer 2.

                LAYER 1 PERCEPTION DATA:
                {risk_assessment}

                LAYER 2 RISK INTELLIGENCE DATA:
                {layer2_mock_data}

                Simulate 3 potential mitigation trade-offs (e.g. Expedite Shipping, Re-source Supplier, Do Nothing).
                Then, formulate a final `MitigationPlan` that optimizes for service-level protection while minimizing cost.

                Return ONLY a valid JSON object matching this exact schema:
                {{
                    "plan_id": "string",
                    "chosen_scenario": {{
                         "scenario_id": "string",
                         "action_type": "string",
                         "estimated_cost_usd": integer,
                         "service_level_impact": "string",
                         "resilience_score": integer
                    }},
                    "supplier_reallocation_target": "string",
                    "buffer_stock_adjustment": integer,
                    "reasoning_tree": "string"
                }}
                """
            )

    def formulate_plan(
        self,
        risk_assessment: SupplyRiskAssessment,
        layer2_risk_data: Optional[Any] = None,
        custom_prompt: Optional[str] = None,
    ) -> MitigationPlan:
        """Formulate plan from Layer 1 assessment and optional Layer 2 risk (RiskAssessmentResponse or dict)."""
        if layer2_risk_data is not None:
            if hasattr(layer2_risk_data, "total_financial_exposure"):
                layer2_str = (
                    f"- Disruption Probability: {getattr(layer2_risk_data, 'disruption_probability', 0):.0%}\n"
                    f"- Revenue at Risk: ${getattr(layer2_risk_data, 'revenue_at_risk', 0):,.0f}\n"
                    f"- Total Financial Exposure: ${getattr(layer2_risk_data, 'total_financial_exposure', 0):,.0f}\n"
                    f"- Risk Level: {getattr(layer2_risk_data, 'risk_level', 'high')}\n"
                    f"- Downtime Days: {getattr(layer2_risk_data, 'downtime_days', 12)}\n"
                    f"- Impacted Part: {getattr(layer2_risk_data, 'affected_part', 'Unknown')}"
                )
            else:
                layer2_str = json.dumps(layer2_risk_data) if isinstance(layer2_risk_data, dict) else str(layer2_risk_data)
        else:
            part = risk_assessment.affected_parts[0] if risk_assessment.affected_parts else "Unknown"
            layer2_str = (
                f"- Disruption Probability: High\n"
                f"- Estimated Revenue at Risk: $2,500,000\n"
                f"- Impacted Part: {part}\n"
                f"- Stockout countdown: 12 days"
            )

        if self.use_mock:
            print(f"\n[Planning Engine] Mock mode: generating plan for {risk_assessment.signal_id}...")
            return _mock_plan_from_layer2(risk_assessment, layer2_risk_data, custom_prompt)

        try:
            chain = self.prompt | self.llm
            print(f"\n[Planning Engine] Simulating trade-offs for: {risk_assessment.signal_id}...")
            response = chain.invoke({
                "risk_assessment": risk_assessment.model_dump_json(),
                "layer2_mock_data": layer2_str,
            })
            clean_json = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return MitigationPlan(**data)
        except Exception as e:
            print(f"Planning LLM Error: {e}. Falling back to mock plan.")
            return _mock_plan_from_layer2(risk_assessment, layer2_risk_data, custom_prompt)
