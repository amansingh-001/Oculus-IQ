from __future__ import annotations

from datetime import datetime, timedelta
import math
import random

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Client, Shipment
from routers.serializers import serialize_shipment
from services.tariff_service import tariff_engine
from services.weather_service import get_weather_risk


router = APIRouter()


class ShipmentUpdateRequest(BaseModel):
    status: str | None = None
    eta: datetime | None = None
    notes: str | None = None


class CreateShipmentRequest(BaseModel):
    client_id: str | None = None
    client_name: str | None = None
    origin_city: str = Field(min_length=2, max_length=120)
    origin_country: str = Field(min_length=2, max_length=120)
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)
    dest_city: str = Field(min_length=2, max_length=120)
    dest_country: str = Field(min_length=2, max_length=120)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lon: float = Field(ge=-180, le=180)
    carrier: str = "Unassigned Operator"
    mode: str = "sea"
    status: str = "pending"
    eta: datetime | None = None
    etd: datetime | None = None
    ata: datetime | None = None
    cargo_value_usd: int = Field(ge=0)
    cargo_type: str = Field(min_length=2, max_length=80)
    container_number: str | None = None
    tracking_number: str | None = None
    operator_name: str | None = None
    vessel_name: str | None = None
    voyage_number: str | None = None
    origin_port_id: str | None = None
    dest_port_id: str | None = None
    dock_terminal: str | None = None
    berth: str | None = None
    customs_status: str = "pending"
    priority: str = "normal"
    incoterm: str | None = None
    hs_code: str | None = None
    po_number: str | None = None
    bl_number: str | None = None
    lc_expiry_date: datetime | None = None
    expected_transit_days: int | None = Field(default=None, ge=0)
    actual_transit_days: int | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    route_distance_km: float | None = Field(default=None, ge=0)
    notes: str | None = None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


async def _next_shipment_id(db: AsyncSession) -> str:
    last_id = await db.scalar(select(Shipment.id).order_by(Shipment.id.desc()).limit(1))
    next_num = int(last_id.split("-")[1]) + 1 if last_id and "-" in last_id else 1
    while await db.get(Shipment, f"SHP-{next_num:06d}") is not None:
        next_num += 1
    return f"SHP-{next_num:06d}"


async def _update_client_counts(db: AsyncSession, client_id: str | None) -> None:
    if not client_id:
        return
    client = await db.get(Client, client_id)
    if client is None:
        return
    result = await db.execute(select(Shipment).where(Shipment.client_id == client_id))
    shipments = result.scalars().all()
    client.active_shipments_count = len([s for s in shipments if s.status in {"pending", "in_transit", "delayed"}])
    client.at_risk_shipments_count = len([s for s in shipments if s.risk_score >= 60])
    client.total_cargo_value_annual_usd = sum(float(s.cargo_value_usd or 0) for s in shipments)


@router.get("")
async def list_shipments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    risk_level: str | None = None,
    carrier: str | None = None,
    mode: str | None = None,
    status: str | None = None,
    client_id: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Shipment)

    if risk_level:
        stmt = stmt.where(Shipment.risk_level == risk_level)
    if carrier:
        stmt = stmt.where(Shipment.carrier == carrier)
    if mode:
        stmt = stmt.where(Shipment.mode == mode)
    if status:
        stmt = stmt.where(Shipment.status == status)
    if client_id:
        stmt = stmt.where(Shipment.client_id == client_id)
    if search:
        stmt = stmt.where(
            Shipment.id.ilike(f"%{search}%")
            | Shipment.client_name.ilike(f"%{search}%")
            | Shipment.bl_number.ilike(f"%{search}%")
            | Shipment.po_number.ilike(f"%{search}%")
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await db.scalar(total_stmt)) or 0)

    stmt = stmt.order_by(Shipment.risk_score.desc(), Shipment.last_updated.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return success_response(
        [serialize_shipment(row) for row in rows],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        },
    )


@router.post("")
async def create_shipment(payload: CreateShipmentRequest, db: AsyncSession = Depends(get_db)):
    client_name = payload.client_name
    if payload.client_id:
        client = await db.get(Client, payload.client_id)
        if client is None:
            raise HTTPException(status_code=404, detail=f"Client {payload.client_id} not found")
        client_name = client.name

    now = datetime.utcnow()
    eta = payload.eta or now + timedelta(days=payload.expected_transit_days or 14)
    etd = payload.etd or now
    route_distance = payload.route_distance_km or round(
        _haversine_km(payload.origin_lat, payload.origin_lon, payload.dest_lat, payload.dest_lon)
        * (1.18 if payload.mode == "air" else 1.35 if payload.mode == "sea" else 1.45),
        1,
    )

    risk_score = 22
    risk_factors = ["Manual cargo registration"]
    if payload.status == "delayed":
        risk_score += 32
        risk_factors.append("Shipment marked delayed at registration")
    if payload.priority in {"high", "urgent"}:
        risk_score += 18
        risk_factors.append(f"{payload.priority.title()} priority cargo")
    if payload.customs_status in {"hold", "inspection", "blocked"}:
        risk_score += 20
        risk_factors.append("Customs status requires intervention")
    if payload.cargo_value_usd >= 1_000_000:
        risk_score += 10
        risk_factors.append("High-value cargo exposure")
    risk_score = min(risk_score, 95)

    shipment = Shipment(
        id=await _next_shipment_id(db),
        client_id=payload.client_id,
        client_name=client_name,
        origin_city=payload.origin_city,
        origin_country=payload.origin_country,
        origin_lat=payload.origin_lat,
        origin_lon=payload.origin_lon,
        dest_city=payload.dest_city,
        dest_country=payload.dest_country,
        dest_lat=payload.dest_lat,
        dest_lon=payload.dest_lon,
        carrier=payload.carrier,
        mode=payload.mode,
        status=payload.status,
        eta=eta,
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        risk_factors=risk_factors,
        current_lat=payload.origin_lat if payload.status == "pending" else (payload.origin_lat + payload.dest_lat) / 2,
        current_lon=payload.origin_lon if payload.status == "pending" else (payload.origin_lon + payload.dest_lon) / 2,
        route_waypoints=[
            {"lat": payload.origin_lat, "lon": payload.origin_lon},
            {"lat": (payload.origin_lat + payload.dest_lat) / 2, "lon": (payload.origin_lon + payload.dest_lon) / 2},
            {"lat": payload.dest_lat, "lon": payload.dest_lon},
        ],
        cargo_value_usd=payload.cargo_value_usd,
        cargo_type=payload.cargo_type,
        container_number=payload.container_number,
        tracking_number=payload.tracking_number,
        operator_name=payload.operator_name or payload.carrier,
        vessel_name=payload.vessel_name,
        voyage_number=payload.voyage_number,
        origin_port_id=payload.origin_port_id,
        dest_port_id=payload.dest_port_id,
        dock_terminal=payload.dock_terminal,
        berth=payload.berth,
        etd=etd,
        ata=payload.ata,
        customs_status=payload.customs_status,
        priority=payload.priority,
        incoterm=payload.incoterm,
        hs_code=payload.hs_code,
        tariff_rate_pct=0.0,
        tariff_adjusted_cost_usd=float(payload.cargo_value_usd),
        po_number=payload.po_number,
        bl_number=payload.bl_number,
        lc_expiry_date=payload.lc_expiry_date,
        expected_transit_days=payload.expected_transit_days or max(1, int((eta - etd).total_seconds() // 86400)),
        actual_transit_days=payload.actual_transit_days,
        weight_kg=payload.weight_kg,
        route_distance_km=route_distance,
        notes=payload.notes,
        source="manual",
        reliability=0.95,
        last_updated=now,
    )
    landed = tariff_engine.calculate_landed_cost(shipment)
    shipment.tariff_rate_pct = landed["tariff_rate_pct"]
    shipment.tariff_adjusted_cost_usd = landed["total_landed_cost_usd"]

    db.add(shipment)
    await db.flush()
    await _update_client_counts(db, payload.client_id)
    await db.commit()
    await db.refresh(shipment)

    return success_response(serialize_shipment(shipment))


@router.get("/stats")
async def shipment_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    rows = result.scalars().all()

    total = len(rows)
    critical = sum(1 for r in rows if r.risk_level == "critical")
    high = sum(1 for r in rows if r.risk_level == "high")
    medium = sum(1 for r in rows if r.risk_level == "medium")
    low = sum(1 for r in rows if r.risk_level == "low")
    delayed = sum(1 for r in rows if r.status == "delayed")
    on_time = sum(1 for r in rows if r.status in {"in_transit", "delivered"})
    total_cargo_value = sum(int(r.cargo_value_usd or 0) for r in rows)

    on_time_rate = round((on_time / total) * 100, 2) if total else 0

    return success_response(
        {
            "total": total,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "delayed": delayed,
            "on_time": on_time,
            "on_time_rate": on_time_rate,
            "total_cargo_value": total_cargo_value,
        }
    )


@router.get("/timeline")
async def shipment_timeline(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    rows = result.scalars().all()

    total = len(rows)
    critical = sum(1 for r in rows if r.risk_level == "critical")
    high = sum(1 for r in rows if r.risk_level == "high")
    medium = sum(1 for r in rows if r.risk_level == "medium")
    low = max(total - (critical + high + medium), 0)

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    points = []

    current = {
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
    }

    for step in range(24):
        timestamp = now - timedelta(hours=23 - step)

        current["critical"] = max(0, current["critical"] + random.randint(-2, 2))
        current["high"] = max(0, current["high"] + random.randint(-3, 3))
        current["medium"] = max(0, current["medium"] + random.randint(-4, 4))

        remaining = total - (current["critical"] + current["high"] + current["medium"])
        if remaining < 0:
            overflow = -remaining
            reduce_medium = min(overflow, current["medium"])
            current["medium"] -= reduce_medium
            overflow -= reduce_medium

            reduce_high = min(overflow, current["high"])
            current["high"] -= reduce_high
            overflow -= reduce_high

            reduce_critical = min(overflow, current["critical"])
            current["critical"] -= reduce_critical

            remaining = total - (current["critical"] + current["high"] + current["medium"])

        current["low"] = max(remaining, 0)

        points.append(
            {
                "hour": timestamp.strftime("%H:%M"),
                "critical": current["critical"],
                "high": current["high"],
                "medium": current["medium"],
                "low": current["low"],
            }
        )

    return success_response(points, meta={"total": len(points)})


@router.get("/financial-summary")
async def financial_summary(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    rows = result.scalars().all()

    at_risk = [r for r in rows if r.risk_score >= 65]
    delayed = [r for r in rows if r.status == "delayed"]
    cargo_at_risk = sum(int(r.cargo_value_usd or 0) for r in at_risk)

    delay_cost = sum(int(r.cargo_value_usd or 0) * 0.002 * 3 for r in delayed)
    rerouting_premium = len(at_risk) * 15_000
    insurance_exposure = cargo_at_risk * 0.0015

    total = delay_cost + rerouting_premium + insurance_exposure

    return success_response({
        "cargo_at_risk_usd": cargo_at_risk,
        "delay_cost_usd": round(delay_cost),
        "rerouting_premium_usd": round(rerouting_premium),
        "insurance_exposure_usd": round(insurance_exposure),
        "total_exposure_usd": round(total),
        "shipments_at_risk": len(at_risk),
        "shipments_delayed": len(delayed),
        "total_cargo_value_usd": sum(int(r.cargo_value_usd or 0) for r in rows),
    })


@router.get("/{shipment_id}")
async def shipment_detail(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    payload = serialize_shipment(shipment)
    payload["weather_overlay"] = await get_weather_risk(shipment.current_lat, shipment.current_lon)
    return success_response(payload)


@router.get("/{shipment_id}/landed-cost")
async def shipment_landed_cost(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    return success_response(tariff_engine.calculate_landed_cost(shipment))


@router.patch("/{shipment_id}")
async def update_shipment(shipment_id: str, payload: ShipmentUpdateRequest, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    if payload.status is not None:
        shipment.status = payload.status
    if payload.eta is not None:
        shipment.eta = payload.eta
    if payload.notes is not None:
        shipment.notes = payload.notes

    shipment.last_updated = datetime.utcnow()
    await db.commit()

    return success_response(serialize_shipment(shipment))
