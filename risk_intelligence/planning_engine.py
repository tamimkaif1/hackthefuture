"""Layer 3 (Tamim): Cost vs service options, net-benefit recommendation."""

from typing import List
from schemas.tamim_schema import RiskAssessmentResponse, PlanOption, PlanningResponse


def simulate_plan_options(risk: RiskAssessmentResponse) -> PlanningResponse:
    baseline_downtime = risk.downtime_days
    revenue_per_day = risk.revenue_at_risk / baseline_downtime if baseline_downtime > 0 else 0
    penalty_per_day = risk.sla_penalty_risk / baseline_downtime if baseline_downtime > 0 else 0

    options: List[PlanOption] = []

    # Option 1: Do nothing
    do_nothing = PlanOption(
        name="Do nothing",
        mitigation_cost=0,
        resulting_downtime_days=baseline_downtime,
        revenue_saved=0,
        penalty_saved=0,
        net_benefit=0,
    )
    options.append(do_nothing)

    # Option 2: Air freight
    airfreight_downtime = max(baseline_downtime - 8, 0)
    airfreight_cost = 350000
    airfreight_revenue_saved = (baseline_downtime - airfreight_downtime) * revenue_per_day
    airfreight_penalty_saved = (baseline_downtime - airfreight_downtime) * penalty_per_day
    airfreight_net = airfreight_revenue_saved + airfreight_penalty_saved - airfreight_cost

    options.append(
        PlanOption(
            name="Air freight critical components",
            mitigation_cost=airfreight_cost,
            resulting_downtime_days=airfreight_downtime,
            revenue_saved=airfreight_revenue_saved,
            penalty_saved=airfreight_penalty_saved,
            net_benefit=airfreight_net,
        )
    )

    # Option 3: Alternate supplier
    alt_downtime = max(baseline_downtime - 5, 0)
    alt_cost = 150000
    alt_revenue_saved = (baseline_downtime - alt_downtime) * revenue_per_day
    alt_penalty_saved = (baseline_downtime - alt_downtime) * penalty_per_day
    alt_net = alt_revenue_saved + alt_penalty_saved - alt_cost

    options.append(
        PlanOption(
            name="Switch partial volume to alternate supplier",
            mitigation_cost=alt_cost,
            resulting_downtime_days=alt_downtime,
            revenue_saved=alt_revenue_saved,
            penalty_saved=alt_penalty_saved,
            net_benefit=alt_net,
        )
    )

    # Option 4: Buffer stock build
    buffer_downtime = max(baseline_downtime - 3, 0)
    buffer_cost = 80000
    buffer_revenue_saved = (baseline_downtime - buffer_downtime) * revenue_per_day
    buffer_penalty_saved = (baseline_downtime - buffer_downtime) * penalty_per_day
    buffer_net = buffer_revenue_saved + buffer_penalty_saved - buffer_cost

    options.append(
        PlanOption(
            name="Increase emergency buffer stock",
            mitigation_cost=buffer_cost,
            resulting_downtime_days=buffer_downtime,
            revenue_saved=buffer_revenue_saved,
            penalty_saved=buffer_penalty_saved,
            net_benefit=buffer_net,
        )
    )

    best_option = max(options, key=lambda x: x.net_benefit)

    return PlanningResponse(
        options=options,
        recommended_option=best_option.name
    )
