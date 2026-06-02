from __future__ import annotations

from typing import Any


def should_generate_alert(
    risk_score: int,
    cargo_value_usd: int,
    disruption_severity: str,
) -> bool:
    severity_ok = disruption_severity in {"high", "critical"}
    return severity_ok and (risk_score >= 75 or cargo_value_usd >= 1_000_000)


def priority_for_risk(score: int) -> str:
    if score >= 90:
        return "urgent"
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def build_recommended_actions(mode: str, risk_level: str) -> list[str]:
    actions = ["Notify internal operations control tower"]
    if mode == "sea":
        actions.append("Evaluate alternate maritime lane and nearest port call")
    elif mode == "air":
        actions.append("Evaluate alternate carrier slot and airport routing")
    else:
        actions.append("Evaluate multimodal reroute to protect ETA")

    if risk_level in {"high", "critical"}:
        actions.append("Prepare customer-facing delay communication draft")

    return actions


def build_alert_title(shipment_id: str, risk_level: str) -> str:
    return f"{risk_level.title()} Risk: {shipment_id} requires intervention"


def build_alert_summary(shipment: Any, disruption: Any | None = None) -> str:
    origin = getattr(shipment, "origin_city", "origin")
    destination = getattr(shipment, "dest_city", "destination")
    if disruption is None:
        return f"Shipment from {origin} to {destination} has elevated risk and should be reviewed."
    return (
        f"Shipment from {origin} to {destination} is impacted by {getattr(disruption, 'title', 'an active disruption')} "
        f"with {getattr(disruption, 'severity', 'medium')} severity."
    )
