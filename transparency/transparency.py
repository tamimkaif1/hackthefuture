"""Layer 6: Explainable reasoning traces, human override thresholds, assumptions, bias and constraint validation."""

from typing import List
from schemas.tamim_schema import TransparencyRequest, TransparencyResponse


def bias_and_constraint_validation(data: TransparencyRequest) -> List[str]:
    """Mock checks: cost bias, constraint (exposure cap), supplier diversity (deterministic, no real audit)."""
    checks = []
    # Constraint: exposure over threshold
    if data.risk_assessment.total_financial_exposure >= 5_000_000:
        checks.append("Constraint: Total financial exposure exceeds $5M; human override required per policy.")
    # Bias: recommend "Do nothing" when exposure is high
    if data.planning_response.recommended_option.lower() == "do nothing" and data.risk_assessment.total_financial_exposure > 1_000_000:
        checks.append("Bias check: 'Do nothing' selected despite high exposure; verify cost-only bias not dominant.")
    # Supplier reallocation
    if "supplier" in data.planning_response.recommended_option.lower() or "alternate" in data.planning_response.recommended_option.lower():
        checks.append("Constraint: Supplier allocation change; ensure dual-source approval documented.")
    if not checks:
        checks.append("Bias and constraint validation: No violations detected for this recommendation.")
    return checks


def build_reasoning_trace(data: TransparencyRequest) -> str:
    return (
        f"1. Perception layer detected {data.perception_output.event_type} "
        f"in {data.perception_output.affected_region} with confidence "
        f"{data.perception_output.confidence:.2f}. "
        f"2. Risk engine mapped the disruption to affected part "
        f"{data.risk_assessment.affected_part}. "
        f"3. Delay of {data.risk_assessment.delay_days} days versus "
        f"{data.risk_assessment.inventory_days} inventory days resulted in "
        f"{data.risk_assessment.downtime_days} downtime days. "
        f"4. Financial exposure was estimated at "
        f"${data.risk_assessment.total_financial_exposure:,.0f}. "
        f"5. Planning engine selected '{data.planning_response.recommended_option}' "
        f"as the best net-benefit option."
    )


def build_transparency(data: TransparencyRequest) -> TransparencyResponse:
    assumptions = [
        "Delay estimate is based on perception layer signal input.",
        "Inventory days are assumed accurate from ERP/manufacturer profile.",
        "Revenue per day and SLA penalty per day are treated as constant.",
        "Planning engine uses simplified mitigation cost assumptions.",
    ]

    human_override_threshold = (
        "Require human approval if total financial exposure exceeds $5M "
        "or if the recommended plan changes supplier allocation."
    )

    return TransparencyResponse(
        reasoning_trace=build_reasoning_trace(data),
        human_override_threshold=human_override_threshold,
        assumptions=assumptions,
        bias_and_constraint_validation=bias_and_constraint_validation(data),
    )
