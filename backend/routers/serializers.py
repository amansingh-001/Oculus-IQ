from __future__ import annotations

from datetime import datetime

from models import Alert, Client, Disruption, ExternalRiskEvent, IntelligenceScan, Shipment


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat() + "Z"


def serialize_shipment(shipment: Shipment) -> dict:
    return {
        "id": shipment.id,
        "client_id": shipment.client_id,
        "client_name": shipment.client_name,
        "origin": {
            "city": shipment.origin_city,
            "country": shipment.origin_country,
            "lat": shipment.origin_lat,
            "lon": shipment.origin_lon,
        },
        "destination": {
            "city": shipment.dest_city,
            "country": shipment.dest_country,
            "lat": shipment.dest_lat,
            "lon": shipment.dest_lon,
        },
        "carrier": shipment.carrier,
        "mode": shipment.mode,
        "status": shipment.status,
        "eta": _iso(shipment.eta),
        "risk_score": shipment.risk_score,
        "risk_level": shipment.risk_level,
        "risk_factors": shipment.risk_factors,
        "current_location": {"lat": shipment.current_lat, "lon": shipment.current_lon},
        "route_waypoints": shipment.route_waypoints,
        "cargo_value_usd": shipment.cargo_value_usd,
        "cargo_type": shipment.cargo_type,
        "container_number": shipment.container_number,
        "tracking_number": shipment.tracking_number,
        "operator_name": shipment.operator_name,
        "vessel_name": shipment.vessel_name,
        "voyage_number": shipment.voyage_number,
        "origin_port_id": shipment.origin_port_id,
        "dest_port_id": shipment.dest_port_id,
        "dock_terminal": shipment.dock_terminal,
        "berth": shipment.berth,
        "etd": _iso(shipment.etd),
        "ata": _iso(shipment.ata),
        "customs_status": shipment.customs_status,
        "priority": shipment.priority,
        "incoterm": shipment.incoterm,
        "hs_code": shipment.hs_code,
        "tariff_rate_pct": shipment.tariff_rate_pct,
        "tariff_adjusted_cost_usd": shipment.tariff_adjusted_cost_usd,
        "po_number": shipment.po_number,
        "bl_number": shipment.bl_number,
        "lc_expiry_date": _iso(shipment.lc_expiry_date),
        "expected_transit_days": shipment.expected_transit_days,
        "actual_transit_days": shipment.actual_transit_days,
        "weight_kg": shipment.weight_kg,
        "route_distance_km": shipment.route_distance_km,
        "notes": shipment.notes,
        "source": shipment.source,
        "reliability": shipment.reliability,
        "last_updated": _iso(shipment.last_updated),
    }


def serialize_client(client: Client, extra: dict | None = None) -> dict:
    payload = {
        "id": client.id,
        "name": client.name,
        "industry": client.industry,
        "country": client.country,
        "city": client.city,
        "primary_contact": client.primary_contact,
        "contact_phone": client.contact_phone,
        "contact_email": client.contact_email,
        "annual_shipment_count": client.annual_shipment_count,
        "total_cargo_value_annual_usd": client.total_cargo_value_annual_usd,
        "risk_tolerance": client.risk_tolerance,
        "sla_on_time_pct": client.sla_on_time_pct,
        "current_sla_performance": client.current_sla_performance,
        "active_shipments_count": client.active_shipments_count,
        "at_risk_shipments_count": client.at_risk_shipments_count,
        "created_at": _iso(client.created_at),
        "notes": client.notes,
    }
    if extra:
        payload.update(extra)
    return payload


def serialize_disruption(disruption: Disruption) -> dict:
    return {
        "id": disruption.id,
        "type": disruption.type,
        "severity": disruption.severity,
        "title": disruption.title,
        "description": disruption.description,
        "affected_region": {
            "lat": disruption.region_lat,
            "lon": disruption.region_lon,
            "radius_km": disruption.radius_km,
        },
        "affected_shipments": disruption.affected_shipments,
        "affected_shipment_count": len(disruption.affected_shipments or []),
        "detected_at": _iso(disruption.detected_at),
        "estimated_delay_hours": disruption.estimated_delay_hours,
        "confidence": disruption.confidence,
        "active": disruption.active,
        "source": disruption.source,
        "source_ref": disruption.source_ref,
        "reliability": disruption.reliability,
        "last_updated": _iso(disruption.last_updated),
    }


def serialize_alert(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "shipment_id": alert.shipment_id,
        "disruption_id": alert.disruption_id,
        "priority": alert.priority,
        "title": alert.title,
        "ai_summary": alert.ai_summary,
        "drafted_notification": alert.drafted_notification,
        "recommended_actions": alert.recommended_actions,
        "created_at": _iso(alert.created_at),
        "acknowledged": alert.acknowledged,
        "acknowledged_at": _iso(alert.acknowledged_at),
        "source": alert.source,
        "reliability": alert.reliability,
        "last_updated": _iso(alert.last_updated),
    }


def serialize_external_risk(event: ExternalRiskEvent) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type,
        "source_event_type": event.source_event_type,
        "severity": event.severity,
        "alert_level": event.alert_level,
        "lat": event.lat,
        "lon": event.lon,
        "radius_km": event.radius_km,
        "url": event.url,
        "active": event.active,
        "source": event.source,
        "source_ref": event.source_ref,
        "detected_at": _iso(event.detected_at),
        "last_updated": _iso(event.last_updated),
    }


def serialize_intelligence_scan(scan: IntelligenceScan) -> dict:
    return {
        "id": scan.id,
        "status": scan.status,
        "scan_type": scan.scan_type,
        "anomalies_count": scan.anomalies_count,
        "sla_clients_at_risk": scan.sla_clients_at_risk,
        "cascade_nodes": scan.cascade_nodes,
        "external_risks_count": scan.external_risks_count,
        "weather_risks_count": scan.weather_risks_count,
        "top_risks": scan.top_risks,
        "summary": scan.summary,
        "created_at": _iso(scan.created_at),
    }
