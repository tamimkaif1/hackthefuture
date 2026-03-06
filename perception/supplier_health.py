"""
Supplier health scoring (Layer 1).
Uses mock data: past_disruptions and ERP to compute a simple health score per supplier.
No real API; scores are deterministic from local JSON and ERP.
"""

import json
import os
from typing import List, Dict

from perception.models import ERPInventorySnapshot


def _load_past_disruptions(log_path: str = "past_disruptions.json") -> List[dict]:
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def compute_supplier_health_scores(
    erp_context: List[ERPInventorySnapshot],
    past_disruptions_path: str = "past_disruptions.json",
) -> Dict[str, dict]:
    """
    Returns a dict: supplier_name -> { "score": 0-100, "disruption_count": int, "label": "Healthy"|"Watch"|"At Risk" }.
    Mock: score derived from number of past disruptions involving that supplier (from ERP part/supplier mapping).
    """
    past = _load_past_disruptions(past_disruptions_path)
    # Build supplier -> part from ERP
    supplier_to_parts: Dict[str, List[str]] = {}
    for p in erp_context:
        supplier_to_parts.setdefault(p.primary_supplier, []).append(p.part_id)

    # Count disruptions per supplier (mock: count events where affected_parts overlap supplier's parts)
    supplier_disruptions: Dict[str, int] = {s: 0 for s in supplier_to_parts}
    for event in past:
        risk = event.get("original_risk") or {}
        if isinstance(risk, dict):
            affected = risk.get("affected_parts") or []
        else:
            affected = getattr(risk, "affected_parts", []) or []
        for supplier, parts in supplier_to_parts.items():
            if any(part in parts for part in affected):
                supplier_disruptions[supplier] = supplier_disruptions.get(supplier, 0) + 1

    result = {}
    for supplier, count in supplier_disruptions.items():
        # Mock scoring: 100 - 15 per disruption, min 0. Label by score.
        score = max(0, min(100, 100 - 15 * count))
        if score >= 70:
            label = "Healthy"
        elif score >= 40:
            label = "Watch"
        else:
            label = "At Risk"
        result[supplier] = {
            "score": score,
            "disruption_count": count,
            "label": label,
        }
    return result


def format_supplier_health_for_summary(scores: Dict[str, dict]) -> str:
    """One-line summary for Layer 1 output."""
    if not scores:
        return "No supplier health data (mock)."
    parts = [f"{s}: {d['label']} ({d['score']})" for s, d in scores.items()]
    return "Supplier health: " + "; ".join(parts)
