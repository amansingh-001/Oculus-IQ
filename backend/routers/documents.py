from __future__ import annotations

import csv
import io
import math
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Client, PortNode, Shipment
from services.geocode_service import geocode_city
from services.gemini_service import gemini_service
from services.risk_engine import RiskEngine
from services.tariff_service import tariff_engine
from services.weather_service import get_weather_risk


router = APIRouter()


class ParseBillOfLadingRequest(BaseModel):
    text: str = Field(min_length=20, max_length=20_000)


class ImportCsvRequest(BaseModel):
    csv_text: str = Field(min_length=10, max_length=100_000)
    upsert: bool = True


CSV_COLUMNS = [
    {"name": "shipment_id", "example": "SHP-000101", "required": True},
    {"name": "client_name", "example": "Apex Textiles Pvt Ltd", "required": True},
    {"name": "origin_city", "example": "Mumbai", "required": True},
    {"name": "origin_country", "example": "India", "required": True},
    {"name": "dest_city", "example": "Hamburg", "required": True},
    {"name": "dest_country", "example": "Germany", "required": True},
    {"name": "carrier", "example": "Maersk", "required": True},
    {"name": "mode", "example": "sea", "required": True},
    {"name": "status", "example": "in_transit", "required": True},
    {"name": "eta", "example": "2026-06-14", "required": True},
    {"name": "cargo_type", "example": "Textiles", "required": True},
    {"name": "cargo_value_usd", "example": "250000", "required": True},
    {"name": "weight_kg", "example": "18000", "required": True},
    {"name": "bl_number", "example": "MAEU123456789", "required": True},
    {"name": "po_number", "example": "PO-2026-1842", "required": True},
    {"name": "incoterm", "example": "FOB", "required": True},
    {"name": "hs_code", "example": "620342", "required": True},
    {"name": "container_number", "example": "CONT123456", "required": True},
]

REQUIRED_COLUMNS = {column["name"] for column in CSV_COLUMNS if column.get("required")}
ALLOWED_MODES = {"sea", "air", "road", "rail", "multimodal"}
ALLOWED_STATUSES = {"pending", "in_transit", "delayed", "delivered"}
_risk_engine = RiskEngine()


def _parse_eta(raw: str, row_index: int) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Row {row_index}: invalid eta '{raw}' (expected YYYY-MM-DD)") from exc


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _resolve_coords(db: AsyncSession, city: str, country: str) -> tuple[float, float, float]:
    stmt = select(PortNode).where(func.lower(PortNode.city) == city.lower())
    if country:
        stmt = stmt.where(func.lower(PortNode.country) == country.lower())
    match = (await db.execute(stmt)).scalars().first()
    if match:
        return match.lat, match.lon, 0.75
    try:
        coords = await geocode_city(city, country)
    except Exception:
        coords = None
    if coords:
        return coords[0], coords[1], 0.65
    return 0.0, 0.0, 0.45


async def _get_or_create_client(db: AsyncSession, name: str) -> Client:
    stmt = select(Client).where(func.lower(Client.name) == name.lower())
    client = (await db.execute(stmt)).scalars().first()
    if client:
        return client

    client_count = int((await db.scalar(select(func.count()).select_from(Client))) or 0)
    client_id = f"CLT-{client_count + 1:03d}"
    client = Client(
        id=client_id,
        name=name,
        industry="Unknown",
        country="",
        city="",
        primary_contact=None,
        contact_phone=None,
        contact_email=None,
        annual_shipment_count=0,
        total_cargo_value_annual_usd=0.0,
        risk_tolerance="medium",
        sla_on_time_pct=95.0,
        current_sla_performance=95.0,
        notes="Imported via CSV",
    )
    db.add(client)
    await db.flush()
    return client


@router.post("/parse-bl")
async def parse_bill_of_lading(payload: ParseBillOfLadingRequest):
    parsed = await gemini_service.parse_bill_of_lading(payload.text)
    return success_response(parsed)


@router.post("/import-csv")
async def import_csv(payload: ImportCsvRequest, db: AsyncSession = Depends(get_db)):
    reader = csv.DictReader(io.StringIO(payload.csv_text))
    fieldnames = reader.fieldnames or []
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        return success_response(
            None,
            meta={
                "error": "CSV missing required columns",
                "missing": sorted(missing),
            },
        )

    rows = [dict(row) for row in reader]
    inserted = 0
    updated = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []

    for index, raw in enumerate(rows, start=2):
        normalized = {key: (value or "").strip() for key, value in raw.items()}
        shipment_id = normalized.get("shipment_id")
        client_name = normalized.get("client_name")

        missing_fields = [field for field in REQUIRED_COLUMNS if not normalized.get(field)]
        if missing_fields:
            errors.append({"row": index, "error": f"missing required fields: {', '.join(missing_fields)}"})
            continue

        status = normalized.get("status", "").lower()
        if status not in ALLOWED_STATUSES:
            errors.append({"row": index, "error": f"invalid status '{status}'"})
            continue

        mode = normalized.get("mode", "").lower()
        if mode not in ALLOWED_MODES:
            errors.append({"row": index, "error": f"invalid mode '{mode}'"})
            continue

        eta_raw = normalized.get("eta", "")
        try:
            eta = _parse_eta(eta_raw, index)
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})
            continue

        try:
            cargo_value = float(normalized.get("cargo_value_usd", 0) or 0)
            weight_kg = float(normalized.get("weight_kg", 0) or 0)
        except ValueError:
            errors.append({"row": index, "error": "cargo_value_usd and weight_kg must be numeric"})
            continue

        client = await _get_or_create_client(db, client_name)

        origin_city = normalized.get("origin_city", "")
        origin_country = normalized.get("origin_country", "")
        dest_city = normalized.get("dest_city", "")
        dest_country = normalized.get("dest_country", "")

        origin_lat, origin_lon, origin_conf = await _resolve_coords(db, origin_city, origin_country)
        dest_lat, dest_lon, dest_conf = await _resolve_coords(db, dest_city, dest_country)
        coord_reliability = round((origin_conf + dest_conf) / 2, 2)

        shipment = await db.get(Shipment, shipment_id)
        if shipment is not None and not payload.upsert:
            skipped += 1
            continue

        weather = await get_weather_risk(origin_lat, origin_lon) if origin_lat or origin_lon else {}
        risk = _risk_engine.calculate_risk(
            {
                "origin_country": origin_country,
                "dest_country": dest_country,
                "mode": mode,
                "carrier": normalized.get("carrier"),
                "cargo_type": normalized.get("cargo_type"),
            },
            weather,
        )

        tariff = tariff_engine.calculate_landed_cost(
            {
                "base_cost_usd": cargo_value * 0.03,
                "cargo_value_usd": cargo_value,
                "hs_code": normalized.get("hs_code"),
                "origin_country": origin_country,
                "dest_country": dest_country,
            }
        )

        route_distance = None
        if origin_lat or origin_lon or dest_lat or dest_lon:
            route_distance = round(_haversine_km(origin_lat, origin_lon, dest_lat, dest_lon) * 1.15, 1)

        waypoints = []
        if origin_lat or origin_lon or dest_lat or dest_lon:
            waypoints = [
                {"lat": origin_lat, "lon": origin_lon},
                {"lat": (origin_lat + dest_lat) / 2, "lon": (origin_lon + dest_lon) / 2},
                {"lat": dest_lat, "lon": dest_lon},
            ]

        payload_values = dict(
            client_id=client.id,
            client_name=client.name,
            origin_city=origin_city,
            origin_country=origin_country,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_city=dest_city,
            dest_country=dest_country,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            carrier=normalized.get("carrier"),
            mode=mode,
            status=status,
            eta=eta,
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            risk_factors=risk["risk_factors"],
            current_lat=origin_lat,
            current_lon=origin_lon,
            route_waypoints=waypoints,
            cargo_value_usd=int(cargo_value),
            cargo_type=normalized.get("cargo_type"),
            container_number=normalized.get("container_number"),
            incoterm=normalized.get("incoterm"),
            hs_code=normalized.get("hs_code"),
            tariff_rate_pct=tariff.get("tariff_rate_pct"),
            tariff_adjusted_cost_usd=tariff.get("total_landed_cost_usd"),
            po_number=normalized.get("po_number"),
            bl_number=normalized.get("bl_number"),
            lc_expiry_date=eta + timedelta(days=30),
            expected_transit_days=None,
            actual_transit_days=None,
            weight_kg=weight_kg,
            route_distance_km=route_distance,
            notes=None,
            source="csv",
            reliability=coord_reliability,
            last_updated=datetime.utcnow(),
        )

        if shipment is None:
            shipment = Shipment(id=shipment_id, **payload_values)
            db.add(shipment)
            inserted += 1
        else:
            for key, value in payload_values.items():
                setattr(shipment, key, value)
            updated += 1

        if len(preview) < 5:
            preview.append({"shipment_id": shipment_id, "client_name": client.name, "status": status})

    await db.commit()

    return success_response(
        {
            "rows_detected": len(rows),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "preview": preview,
        }
    )


@router.get("/template")
async def csv_template():
    return success_response(
        {
            "format": "csv",
            "columns": CSV_COLUMNS,
            "example_row": {column["name"]: column["example"] for column in CSV_COLUMNS},
            "notes": "Computed fields (risk_score, coordinates, waypoints) are system-generated after import.",
        }
    )
