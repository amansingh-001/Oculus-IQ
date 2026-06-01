from __future__ import annotations

from typing import Any


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


class NotificationService:
    def generate_whatsapp_alert(
        self,
        shipment: Any,
        disruption: Any | None = None,
        alternatives: list[dict[str, Any]] | None = None,
    ) -> str:
        client_name = _get(shipment, "client_name") or "Client"
        ship_id = _get(shipment, "id", "shipment")
        origin = _get(shipment, "origin_city", "Origin")
        dest = _get(shipment, "dest_city", "Destination")
        disruption_title = _get(disruption, "title", "Elevated disruption risk") if disruption else "Elevated disruption risk"
        delay_hours = _get(disruption, "estimated_delay_hours", 48) if disruption else 48
        delay_days = round(float(delay_hours or 48) / 24, 1)

        best_alt = alternatives[0] if alternatives else None
        alt_text = ""
        if best_alt:
            alt_text = (
                f"\nRecommended action: {best_alt.get('route_name', 'Review route alternative')}"
                f"\nNew ETA impact: +{best_alt.get('total_days', 'TBD')} days"
                f" | Additional cost: ${float(best_alt.get('base_cost_usd', 0) or 0):,.0f}"
            )

        return (
            f"Supply Chain Alert - {client_name}\n\n"
            f"Shipment: {ship_id}\n"
            f"Route: {origin} -> {dest}\n"
            f"Issue: {disruption_title}\n"
            f"Expected delay: {delay_days} days\n"
            f"{alt_text}\n\n"
            "Our team is monitoring this shipment and will provide another update in 4 hours.\n\n"
            "Powered by OculusIQ Freight Intelligence"
        )

    def generate_client_weekly_report(self, client: Any, shipments: list[Any]) -> dict[str, Any]:
        total = len(shipments)
        on_time = len([
            s for s in shipments
            if _get(s, "status") in {"delivered", "in_transit"} and (_get(s, "risk_score", 0) or 0) < 60
        ])
        delayed = len([s for s in shipments if _get(s, "status") == "delayed"])
        at_risk = len([s for s in shipments if (_get(s, "risk_score", 0) or 0) >= 60])
        on_time_rate = round((on_time / max(total, 1)) * 100, 1)
        sla_target = float(_get(client, "sla_on_time_pct", 95.0) or 95.0)
        top_risk = sorted(shipments, key=lambda s: _get(s, "risk_score", 0) or 0, reverse=True)[:3]

        return {
            "client_id": _get(client, "id"),
            "client_name": _get(client, "name"),
            "report_period": "This Week",
            "total_active_shipments": total,
            "on_time_count": on_time,
            "on_time_rate": on_time_rate,
            "delayed_count": delayed,
            "at_risk_count": at_risk,
            "sla_target": sla_target,
            "sla_status": "MET" if on_time_rate >= sla_target else "BREACH RISK",
            "top_risk_shipments": [_get(s, "id") for s in top_risk],
            "total_cargo_value_monitored": sum(float(_get(s, "cargo_value_usd", 0) or 0) for s in shipments),
        }


notification_service = NotificationService()
