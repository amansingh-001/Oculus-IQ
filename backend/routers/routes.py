from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Disruption, PortNode, RouteEdge, Shipment
from routers.serializers import serialize_disruption, serialize_shipment
from services.route_optimizer import get_route_alternatives, route_graph


router = APIRouter()
_cache: dict[str, tuple[datetime, list[dict[str, Any]], str | None]] = {}
_cache_ttl = timedelta(minutes=10)


class OptimizeRequest(BaseModel):
    origin_port_id: str
    dest_port_id: str
    optimize_for: str = Field(default="balanced")


class CreateRouteRequest(BaseModel):
    from_port_id: str
    to_port_id: str
    mode: str = "sea"
    distance_km: float = Field(gt=0)
    base_transit_hours: float = Field(gt=0)
    base_cost_usd_per_teu: float = Field(ge=0)
    reliability_score: float = Field(default=85.0, ge=0, le=100)
    current_delay_factor: float = Field(default=1.0, ge=0.1)


@router.get("/{shipment_id}/alternatives")
async def route_alternatives(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    disruption_result = await db.execute(
        select(Disruption)
        .where(Disruption.active.is_(True))
        .order_by(Disruption.detected_at.desc())
    )
    disruptions = disruption_result.scalars().all()

    active_disruption = next((d for d in disruptions if shipment.id in (d.affected_shipments or [])), None)

    disruption_key = active_disruption.id if active_disruption else "none"
    cache_key = f"{shipment_id}:{disruption_key}"
    now = datetime.utcnow()

    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return success_response(
            {
                "shipment_id": shipment.id,
                "disruption_id": disruption_key,
                "alternatives": cached[1],
                "source": "cache",
            }
        )

    shipment_payload = serialize_shipment(shipment)
    disruption_payload = serialize_disruption(active_disruption) if active_disruption else None
    alternatives = await get_route_alternatives(shipment_payload, disruption_payload)

    _cache[cache_key] = (now + _cache_ttl, alternatives, disruption_key)

    return success_response(
        {
            "shipment_id": shipment.id,
            "disruption_id": disruption_key,
            "alternatives": alternatives,
            "source": "ai",
        }
    )


@router.post("/optimize")
async def optimize_route(payload: OptimizeRequest, db: AsyncSession = Depends(get_db)):
    """On-demand route optimization between any two ports."""
    if not route_graph.nodes:
        await route_graph.load_from_db(db)

    routes = route_graph.find_k_shortest(
        payload.origin_port_id,
        payload.dest_port_id,
        k=3,
        optimize_for=payload.optimize_for,
    )
    return success_response(routes, meta={"total": len(routes)})


@router.post("")
async def create_route(payload: CreateRouteRequest, db: AsyncSession = Depends(get_db)):
    origin = await db.get(PortNode, payload.from_port_id)
    dest = await db.get(PortNode, payload.to_port_id)
    if origin is None:
        raise HTTPException(status_code=404, detail=f"Port {payload.from_port_id} not found")
    if dest is None:
        raise HTTPException(status_code=404, detail=f"Port {payload.to_port_id} not found")

    edge = RouteEdge(
        from_port_id=payload.from_port_id,
        to_port_id=payload.to_port_id,
        mode=payload.mode,
        distance_km=payload.distance_km,
        base_transit_hours=payload.base_transit_hours,
        base_cost_usd_per_teu=payload.base_cost_usd_per_teu,
        current_delay_factor=payload.current_delay_factor,
        reliability_score=payload.reliability_score,
        is_active=True,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    await route_graph.load_from_db(db)

    return success_response({
        "id": edge.id,
        "from_port_id": edge.from_port_id,
        "to_port_id": edge.to_port_id,
        "mode": edge.mode,
        "distance_km": edge.distance_km,
        "base_transit_hours": edge.base_transit_hours,
        "base_cost_usd_per_teu": edge.base_cost_usd_per_teu,
        "current_delay_factor": edge.current_delay_factor,
        "reliability_score": edge.reliability_score,
        "is_active": edge.is_active,
    })


@router.get("/network")
async def get_network(db: AsyncSession = Depends(get_db)):
    """Return the full port network as GeoJSON for map visualization."""
    if not route_graph.nodes:
        await route_graph.load_from_db(db)
    geojson = route_graph.get_network_geojson()
    return success_response(geojson)


@router.get("/chokepoints")
async def get_chokepoints(db: AsyncSession = Depends(get_db)):
    """Return all global chokepoints with current status."""
    if not route_graph.nodes:
        await route_graph.load_from_db(db)
    chokepoints = route_graph.get_chokepoints()
    return success_response(chokepoints, meta={"total": len(chokepoints)})
