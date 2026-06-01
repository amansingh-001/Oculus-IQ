"""Ports router — Port congestion and network endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import PortNode
from services.port_service import port_congestion_engine
from services.route_optimizer import route_graph


router = APIRouter()


class CreatePortRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=2, max_length=160)
    city: str | None = None
    country: str | None = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    type: str = "sea_port"
    capacity_teu: int | None = Field(default=None, ge=0)


async def _next_port_id(db: AsyncSession, payload: CreatePortRequest) -> str:
    if payload.id:
        port_id = payload.id.strip().upper().replace(" ", "_")[:20]
        if await db.get(PortNode, port_id) is not None:
            raise HTTPException(status_code=409, detail=f"Port {port_id} already exists")
        return port_id
    count = int((await db.scalar(select(func.count()).select_from(PortNode))) or 0) + 1
    prefix = "AIR" if payload.type == "air_hub" else "CHK" if payload.type == "chokepoint" else "PRT"
    while await db.get(PortNode, f"{prefix}{count:04d}") is not None:
        count += 1
    return f"{prefix}{count:04d}"


@router.post("")
async def create_port(payload: CreatePortRequest, db: AsyncSession = Depends(get_db)):
    port = PortNode(
        id=await _next_port_id(db, payload),
        name=payload.name,
        city=payload.city,
        country=payload.country,
        lat=payload.lat,
        lon=payload.lon,
        type=payload.type,
        capacity_teu=payload.capacity_teu,
        congestion_score=0.0,
        avg_wait_hours=0.0,
        is_active=True,
        source="manual",
        reliability=0.95,
        last_updated=datetime.utcnow(),
    )
    db.add(port)
    await db.commit()
    await db.refresh(port)
    await route_graph.load_from_db(db)

    congestion = port_congestion_engine.get_port_congestion(port.id)
    return success_response({
        "id": port.id,
        "port_id": port.id,
        "name": port.name,
        "city": port.city,
        "country": port.country,
        "lat": port.lat,
        "lon": port.lon,
        "type": port.type,
        "capacity_teu": port.capacity_teu,
        "source": port.source,
        "last_updated": port.last_updated.isoformat() + "Z",
        **congestion,
    })


@router.get("/congestion")
async def get_all_congestion(db: AsyncSession = Depends(get_db)):
    """Get congestion scores for all ports."""
    result = await db.execute(select(PortNode))
    ports = result.scalars().all()

    congestion_data = []
    for port in ports:
        congestion = port_congestion_engine.get_port_congestion(port.id)
        congestion["name"] = port.name
        congestion["city"] = port.city
        congestion["country"] = port.country
        congestion["lat"] = port.lat
        congestion["lon"] = port.lon
        congestion["type"] = port.type
        congestion["capacity_teu"] = port.capacity_teu
        congestion["port_source"] = port.source
        congestion["port_last_updated"] = port.last_updated.isoformat() + "Z"
        congestion["port_reliability"] = port.reliability
        congestion_data.append(congestion)

    return success_response(congestion_data, meta={"total": len(congestion_data)})


@router.get("/{port_id}")
async def get_port_detail(port_id: str, db: AsyncSession = Depends(get_db)):
    port = await db.get(PortNode, port_id)
    if not port:
        return success_response(None, meta={"error": "Port not found"})

    congestion = port_congestion_engine.get_port_congestion(port.id)
    return success_response({
        "id": port.id,
        "name": port.name,
        "city": port.city,
        "country": port.country,
        "lat": port.lat,
        "lon": port.lon,
        "type": port.type,
        "capacity_teu": port.capacity_teu,
        "port_source": port.source,
        "port_last_updated": port.last_updated.isoformat() + "Z",
        "port_reliability": port.reliability,
        **congestion,
    })
