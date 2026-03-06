"""
Adapter: Layer 1 (Perception) output -> Tamim's Layer 2 input.
Maps SupplyRiskAssessment + NewsSignal + ERP context to PerceptionOutput and ManufacturerProfile.
"""

import json
import os
from typing import List

from perception.models import SupplyRiskAssessment, NewsSignal, ERPInventorySnapshot
from schemas.tamim_schema import PerceptionOutput, ManufacturerProfile

# Default config path relative to project root
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

_PROBABILITY_TO_CONFIDENCE = {"Low": 0.3, "Medium": 0.6, "High": 0.9}


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {
        "company_name": "Supply Chain Co",
        "revenue_per_day": 500000,
        "sla_penalty_per_day": 100000,
        "inventory_days": {},
        "critical_parts": [],
    }


def _infer_event_type(news: NewsSignal) -> str:
    headline_lower = (news.headline or "").lower()
    if "typhoon" in headline_lower or "port" in headline_lower or "shipping" in headline_lower:
        return "shipping_delay"
    if "fire" in headline_lower or "fab" in headline_lower or "factory" in headline_lower:
        return "factory_disruption"
    return "supply_disruption"


def _delay_days_from_erp(affected_parts: List[str], erp_context: List[ERPInventorySnapshot]) -> int:
    part_ids = {p.part_id for p in erp_context}
    max_lead = 0
    for part_id in affected_parts:
        if part_id in part_ids:
            for p in erp_context:
                if p.part_id == part_id:
                    max_lead = max(max_lead, p.lead_time_days)
                    break
    return max_lead if max_lead > 0 else 14


def to_perception_output(
    assessment: SupplyRiskAssessment,
    news: NewsSignal,
    erp_context: List[ERPInventorySnapshot],
) -> PerceptionOutput:
    """Build Tamim's PerceptionOutput from Layer 1 outputs."""
    confidence = _PROBABILITY_TO_CONFIDENCE.get(
        assessment.probability.strip(),
        assessment.risk_score / 10.0,
    )
    affected_region = (news.location or "").strip() or "Unknown"
    affected_suppliers = list({p.primary_supplier for p in erp_context if p.part_id in assessment.affected_parts})
    if not affected_suppliers and erp_context:
        affected_suppliers = [erp_context[0].primary_supplier]

    delay_days = _delay_days_from_erp(assessment.affected_parts, erp_context)

    return PerceptionOutput(
        event_type=_infer_event_type(news),
        affected_region=affected_region,
        confidence=round(confidence, 2),
        affected_suppliers=affected_suppliers,
        affected_parts=assessment.affected_parts,
        delay_days_estimate=delay_days,
    )


def get_manufacturer_profile(erp_context: List[ERPInventorySnapshot]) -> ManufacturerProfile:
    """Build ManufacturerProfile from config and ERP (inventory_days can come from config or ERP)."""
    cfg = _load_config()
    inventory_days = dict(cfg.get("inventory_days", {}))
    # Override from ERP: use lead_time_days as proxy if part not in config (simplified)
    for p in erp_context:
        if p.part_id not in inventory_days:
            # Rough proxy: assume we have some days of stock
            inventory_days[p.part_id] = max(1, min(p.lead_time_days, p.current_stock // 100))
    critical_parts = cfg.get("critical_parts", []) or [p.part_id for p in erp_context]
    return ManufacturerProfile(
        company_name=cfg.get("company_name", "Supply Chain Co"),
        revenue_per_day=float(cfg.get("revenue_per_day", 500000)),
        inventory_days=inventory_days,
        sla_penalty_per_day=float(cfg.get("sla_penalty_per_day", 100000)),
        critical_parts=critical_parts,
    )
