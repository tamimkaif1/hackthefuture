"""Layer 4: Auto-generated supplier emails, PO adjustments, executive alerts, escalation triggers, workflow log."""

from schemas.tamim_schema import ActionRequest, ActionResponse


def _fallback_supplier_email(data: ActionRequest) -> str:
    return (
        f"Subject: Urgent supply update request for {data.risk_assessment.affected_part}\n\n"
        f"Hello {data.manufacturer_profile.company_name} supplier team,\n\n"
        f"We are monitoring a {data.risk_assessment.event_type} affecting "
        f"{data.risk_assessment.affected_part}. Based on our current assessment, "
        f"we estimate {data.risk_assessment.delay_days} days of disruption risk.\n\n"
        f"Please confirm revised ETAs, available allocation, and any expedited shipping options.\n\n"
        f"Regards,\nSupply Chain Team"
    )


def _fallback_executive_alert(data: ActionRequest) -> str:
    return (
        f"Executive Alert: {data.risk_assessment.risk_level.upper()} risk detected.\n"
        f"Revenue at risk: ${data.risk_assessment.revenue_at_risk:,.0f}\n"
        f"SLA penalty risk: ${data.risk_assessment.sla_penalty_risk:,.0f}\n"
        f"Recommended action: {data.planning_response.recommended_option}"
    )


def _fallback_po_adjustment(data: ActionRequest) -> str:
    return (
        f"Increase safety stock for {data.risk_assessment.affected_part} and review reorder points "
        f"based on a projected {data.risk_assessment.delay_days}-day delay. "
        f"Recommended plan: {data.planning_response.recommended_option}."
    )


def _escalation_trigger(data: ActionRequest) -> str:
    """Escalation triggers: e.g. notify VP when risk is critical (mock: deterministic)."""
    if data.risk_assessment.risk_level == "critical":
        return "ESCALATION: Notify VP Supply Chain; total financial exposure exceeds $10M."
    if data.risk_assessment.risk_level == "high":
        return "ESCALATION: Notify Supply Chain Manager; exposure exceeds $5M."
    return ""


def _workflow_integration_log(data: ActionRequest) -> list:
    """Mock workflow integrations: log where actions would be sent (no real integrations)."""
    return [
        "Workflow: Supplier email queued for outbound (mock).",
        "Workflow: Executive alert sent to dashboard (mock).",
        "Workflow: PO adjustment suggestion written to ERP change log (mock).",
    ]


def generate_actions(data: ActionRequest) -> ActionResponse:
    return ActionResponse(
        supplier_email=_fallback_supplier_email(data),
        executive_alert=_fallback_executive_alert(data),
        po_adjustment_suggestion=_fallback_po_adjustment(data),
        escalation_trigger=_escalation_trigger(data),
        workflow_integration_log=_workflow_integration_log(data),
    )
