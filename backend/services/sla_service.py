from __future__ import annotations

from typing import Any


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


class SLABreachPredictor:
    def check_client_sla_risk(self, client: Any, client_shipments: list[Any]) -> dict[str, Any]:
        monitored = [s for s in client_shipments if _get(s, "status") in {"in_transit", "delivered", "delayed"}]
        if not monitored:
            return {
                "client_id": _get(client, "id"),
                "client_name": _get(client, "name"),
                "status": "no_data",
                "urgency": "low",
                "action_required": False,
                "recommended_action": "No active shipment data available.",
            }

        likely_delayed = [
            s for s in monitored
            if _get(s, "status") == "delayed" or (_get(s, "risk_score", 0) or 0) >= 60
        ]
        delivered_or_safe = len(monitored) - len(likely_delayed)
        projected_on_time = (delivered_or_safe / max(len(monitored), 1)) * 100
        sla_target = float(_get(client, "sla_on_time_pct", 95.0) or 95.0)
        sla_gap = projected_on_time - sla_target

        if projected_on_time < sla_target - 10:
            status = "breach_likely"
            urgency = "critical"
        elif projected_on_time < sla_target:
            status = "breach_risk"
            urgency = "high"
        elif projected_on_time < sla_target + 5:
            status = "marginal"
            urgency = "medium"
        else:
            status = "healthy"
            urgency = "low"

        return {
            "client_id": _get(client, "id"),
            "client_name": _get(client, "name"),
            "sla_target_pct": sla_target,
            "current_on_time_pct": round(projected_on_time, 1),
            "sla_gap": round(sla_gap, 1),
            "at_risk_shipments": len(likely_delayed),
            "total_monitored": len(monitored),
            "status": status,
            "urgency": urgency,
            "action_required": urgency in {"critical", "high"},
            "recommended_action": self._get_sla_action(status, len(likely_delayed), _get(client, "name", "this client")),
        }

    def _get_sla_action(self, status: str, at_risk_count: int, client_name: str) -> str:
        if status == "breach_likely":
            return f"Immediate: Contact {client_name} about {at_risk_count} at-risk shipments and consider expediting the top value lanes."
        if status == "breach_risk":
            return f"Monitor closely: {at_risk_count} shipments may breach SLA. Prepare a contingency plan."
        if status == "marginal":
            return "Watch list: SLA margin is tight. Review high-risk shipments daily."
        return "No action required."


sla_predictor = SLABreachPredictor()
