"""Layer 2: Disruption probability, downtime, revenue-at-risk, SLA penalty, risk level."""

from schemas.tamim_schema import RiskAssessmentResponse


def calculate_downtime(delay_days: int, inventory_days: int) -> int:
    return max(delay_days - inventory_days, 0)


def calculate_revenue_at_risk(revenue_per_day: float, downtime_days: int) -> float:
    return revenue_per_day * downtime_days


def calculate_sla_penalty(sla_penalty_per_day: float, downtime_days: int) -> float:
    return sla_penalty_per_day * downtime_days


def classify_risk_level(total_financial_exposure: float) -> str:
    if total_financial_exposure >= 10000000:
        return "critical"
    elif total_financial_exposure >= 5000000:
        return "high"
    elif total_financial_exposure >= 1000000:
        return "medium"
    return "low"


def assess_risk(perception_output: dict, manufacturer_profile: dict) -> RiskAssessmentResponse:
    part = perception_output["affected_parts"][0]
    delay_days = perception_output["delay_days_estimate"]
    inventory_days = manufacturer_profile["inventory_days"].get(part, 0)

    downtime_days = calculate_downtime(delay_days, inventory_days)
    revenue_at_risk = calculate_revenue_at_risk(
        manufacturer_profile["revenue_per_day"],
        downtime_days
    )
    sla_penalty = calculate_sla_penalty(
        manufacturer_profile["sla_penalty_per_day"],
        downtime_days
    )
    total_financial_exposure = revenue_at_risk + sla_penalty

    return RiskAssessmentResponse(
        event_type=perception_output["event_type"],
        affected_part=part,
        disruption_probability=perception_output["confidence"],
        delay_days=delay_days,
        inventory_days=inventory_days,
        downtime_days=downtime_days,
        revenue_at_risk=revenue_at_risk,
        sla_penalty_risk=sla_penalty,
        total_financial_exposure=total_financial_exposure,
        risk_level=classify_risk_level(total_financial_exposure)
    )


if __name__ == "__main__":
    perception_output = {
        "event_type": "shipping_delay",
        "affected_region": "Red Sea",
        "confidence": 0.82,
        "affected_suppliers": ["TaiwanChip Co"],
        "affected_parts": ["semiconductor_control_unit"],
        "delay_days_estimate": 21
    }

    manufacturer_profile = {
        "company_name": "Helios Drive Systems GmbH",
        "revenue_per_day": 700000,
        "inventory_days": {
            "semiconductor_control_unit": 9
        },
        "sla_penalty_per_day": 120000,
        "critical_parts": ["semiconductor_control_unit"]
    }

    result = assess_risk(perception_output, manufacturer_profile)
    print(result)
