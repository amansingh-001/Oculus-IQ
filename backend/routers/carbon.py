from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Client, Shipment
from routers.serializers import serialize_shipment
from services.carbon_service import carbon_tracker
from services.route_optimizer import get_route_alternatives


router = APIRouter()


@router.get("/shipment/{shipment_id}")
async def shipment_carbon(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return success_response(carbon_tracker.calculate_shipment_carbon(shipment))


@router.get("/fleet-summary")
async def fleet_summary(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    shipments = result.scalars().all()
    analyses = [carbon_tracker.calculate_shipment_carbon(s) for s in shipments]
    by_mode: dict[str, float] = {}
    for analysis in analyses:
        by_mode[analysis["mode"]] = by_mode.get(analysis["mode"], 0) + analysis["co2_tonnes"]
    return success_response(
        {
            "shipments_analyzed": len(analyses),
            "total_co2_tonnes": round(sum(a["co2_tonnes"] for a in analyses), 2),
            "total_cbam_cost_eur": round(sum(a["cbam_cost_eur"] for a in analyses), 2),
            "by_mode_tonnes": {mode: round(value, 2) for mode, value in by_mode.items()},
        }
    )


@router.get("/client/{client_id}")
async def client_carbon(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    result = await db.execute(select(Shipment).where(Shipment.client_id == client_id))
    shipments = result.scalars().all()
    analyses = [carbon_tracker.calculate_shipment_carbon(s) for s in shipments]
    return success_response(
        {
            "client_id": client.id,
            "client_name": client.name,
            "shipments_analyzed": len(analyses),
            "total_co2_tonnes": round(sum(a["co2_tonnes"] for a in analyses), 2),
            "total_cbam_cost_eur": round(sum(a["cbam_cost_eur"] for a in analyses), 2),
        }
    )


@router.get("/route-comparison/{shipment_id}")
async def route_carbon_comparison(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    alternatives = await get_route_alternatives(serialize_shipment(shipment), None)
    return success_response(
        {
            "shipment_id": shipment.id,
            "routes": carbon_tracker.compare_route_carbon(alternatives, shipment),
        }
    )
