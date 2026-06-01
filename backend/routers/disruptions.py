from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from data.seed_shipments import next_disruption_scenario
from models import Alert, Disruption, Shipment
from routers.serializers import serialize_disruption
from services.alert_service import (
    build_alert_summary,
    build_alert_title,
    build_recommended_actions,
    priority_for_risk,
    should_generate_alert,
)
from services.risk_engine import RiskEngine
from services.weather_service import get_weather_risk


router = APIRouter()
_risk_engine = RiskEngine()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class SimulateDisruptionRequest(BaseModel):
    type: str | None = None
    region: str | None = None
    severity: str | None = None
    lat: float | None = None
    lon: float | None = None
    radius_km: int | None = None
    duration_hours: int | None = None
    target_type: str | None = None
    client_id: str | None = None
    shipment_id: str | None = None
    operator_name: str | None = None


async def _build_weather_zones(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Disruption).where(Disruption.active.is_(True)).order_by(Disruption.detected_at.desc()).limit(8)
    )
    disruptions = result.scalars().all()

    zones = []
    for disruption in disruptions:
        if disruption.type != "weather":
            continue
        weather = await get_weather_risk(disruption.region_lat, disruption.region_lon)
        zones.append(
            {
                "disruption_id": disruption.id,
                "title": disruption.title,
                "lat": disruption.region_lat,
                "lon": disruption.region_lon,
                "radius_km": disruption.radius_km,
                "wind_kmh": weather.get("wind_kmh"),
                "precipitation_mm": weather.get("precipitation_mm"),
                "risk_level": weather.get("risk_level"),
            }
        )

    return zones


@router.get("")
async def list_disruptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Disruption).where(Disruption.active.is_(True)).order_by(Disruption.detected_at.desc())
    )
    disruptions = result.scalars().all()

    shipment_result = await db.execute(select(Shipment).where(Shipment.status == "in_transit"))
    shipments = shipment_result.scalars().all()

    payloads = []
    for disruption in disruptions:
        affected_ids = []
        for shipment in shipments:
            distance = _haversine_km(
                shipment.current_lat,
                shipment.current_lon,
                disruption.region_lat,
                disruption.region_lon,
            )
            if distance <= disruption.radius_km:
                affected_ids.append(shipment.id)

        payload = serialize_disruption(disruption)
        payload["affected_shipments"] = affected_ids
        payload["affected_shipment_count"] = len(affected_ids)
        payloads.append(payload)

    return success_response(payloads, meta={"total": len(payloads)})


@router.post("/simulate")
async def simulate_disruption(payload: SimulateDisruptionRequest, db: AsyncSession = Depends(get_db)):
    scenario = next_disruption_scenario()

    disruption_type = payload.type or scenario["type"]
    disruption_region = payload.region or scenario["region"]
    disruption_severity = payload.severity or scenario["severity"]
    lat = float(payload.lat if payload.lat is not None else scenario["lat"])
    lon = float(payload.lon if payload.lon is not None else scenario["lon"])
    radius_km = int(payload.radius_km or scenario["radius_km"])
    duration_hours = int(payload.duration_hours or scenario["estimated_delay_hours"])

    disruption_count = int((await db.scalar(select(func.count()).select_from(Disruption))) or 0)
    disruption_id = f"DIS-{disruption_count + 1:04d}"

    disruption = Disruption(
        id=disruption_id,
        type=disruption_type,
        severity=disruption_severity,
        title=f"{disruption_region} {disruption_type.title()} Scenario",
        description=f"Simulated {disruption_type} disruption in {disruption_region}.",
        region_lat=lat,
        region_lon=lon,
        radius_km=radius_km,
        affected_shipments=[],
        detected_at=datetime.utcnow(),
        estimated_delay_hours=duration_hours,
        confidence=0.87,
        active=True,
        source="simulate",
        source_ref=None,
        reliability=0.6,
        last_updated=datetime.utcnow(),
    )

    updated_shipments = []
    created_alerts = 0
    last_alert_id = await db.scalar(select(Alert.id).order_by(Alert.id.desc()).limit(1))
    next_alert_num = int(last_alert_id.split("-")[1]) + 1 if last_alert_id else 1

    db.add(disruption)
    await db.flush()

    shipment_result = await db.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "delayed", "pending"]))
    )
    shipments = shipment_result.scalars().all()
    target_type = payload.target_type or "all"
    if target_type == "client" and payload.client_id:
        shipments = [shipment for shipment in shipments if shipment.client_id == payload.client_id]
    elif target_type == "shipment" and payload.shipment_id:
        shipments = [shipment for shipment in shipments if shipment.id == payload.shipment_id]
    elif target_type == "operator" and payload.operator_name:
        operator = payload.operator_name.lower()
        shipments = [
            shipment
            for shipment in shipments
            if operator in ((shipment.operator_name or shipment.carrier or "").lower())
        ]

    for shipment in shipments:
        distance = _haversine_km(
            shipment.current_lat,
            shipment.current_lon,
            disruption.region_lat,
            disruption.region_lon,
        )
        if distance > disruption.radius_km:
            continue

        disruption.affected_shipments.append(shipment.id)
        weather = await get_weather_risk(shipment.current_lat, shipment.current_lon)
        risk = _risk_engine.calculate_risk(shipment, weather, disruption)

        shipment.risk_score = risk["risk_score"]
        shipment.risk_level = risk["risk_level"]
        shipment.risk_factors = risk["risk_factors"]
        shipment.last_updated = datetime.utcnow()

        updated_shipments.append(
            {
                "shipment_id": shipment.id,
                "new_risk": shipment.risk_score,
                "new_level": shipment.risk_level,
            }
        )

        if should_generate_alert(shipment.risk_score, shipment.cargo_value_usd, disruption.severity):
            existing_alert = await db.scalar(
                select(Alert).where(
                    Alert.shipment_id == shipment.id,
                    Alert.disruption_id == disruption.id,
                )
            )
            if existing_alert is not None:
                continue

            alert = Alert(
                id=f"ALT-{next_alert_num:04d}",
                shipment_id=shipment.id,
                disruption_id=disruption.id,
                priority=priority_for_risk(shipment.risk_score),
                title=build_alert_title(shipment.id, shipment.risk_level),
                ai_summary=build_alert_summary(shipment, disruption),
                drafted_notification=None,
                recommended_actions=build_recommended_actions(shipment.mode, shipment.risk_level),
                created_at=datetime.utcnow(),
                acknowledged=False,
                source="simulate",
                reliability=0.65,
                last_updated=datetime.utcnow(),
            )
            db.add(alert)
            created_alerts += 1
            next_alert_num += 1

    await db.commit()

    return success_response(
        {
            "disruption_id": disruption.id,
            "type": disruption.type,
            "region": disruption_region,
            "severity": disruption.severity,
            "target_type": target_type,
            "target_ref": payload.client_id or payload.shipment_id or payload.operator_name,
            "affected_shipments": len(disruption.affected_shipments),
            "alerts_created": created_alerts,
            "updated_shipment_risks": updated_shipments[:50],
        }
    )


@router.get("/weather")
async def weather_risk_zones(db: AsyncSession = Depends(get_db)):
    zones = await _build_weather_zones(db)
    return success_response(zones, meta={"total": len(zones)})
