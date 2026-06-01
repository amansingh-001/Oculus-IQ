from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Shipment
from routers.serializers import serialize_shipment
from services.route_optimizer import get_route_alternatives
from services.tariff_service import tariff_engine


router = APIRouter()


@router.get("/shipment/{shipment_id}")
async def shipment_tariff(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return success_response(tariff_engine.calculate_landed_cost(shipment))


@router.get("/route-comparison/{shipment_id}")
async def route_tariff_comparison(shipment_id: str, db: AsyncSession = Depends(get_db)):
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    alternatives = await get_route_alternatives(serialize_shipment(shipment), None)
    return success_response(
        {
            "shipment_id": shipment.id,
            "routes": tariff_engine.compare_route_tariffs(shipment, alternatives),
        }
    )


@router.get("/high-exposure")
async def high_exposure(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    shipments = result.scalars().all()
    rows = []
    for shipment in shipments:
        analysis = tariff_engine.calculate_landed_cost(shipment)
        if analysis["tariff_flag"]:
            rows.append({**serialize_shipment(shipment), "landed_cost": analysis})
    rows.sort(key=lambda item: item["landed_cost"]["tariff_amount_usd"], reverse=True)
    return success_response(rows[:100], meta={"total": len(rows)})


@router.get("/fleet-exposure")
async def fleet_exposure(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment))
    shipments = result.scalars().all()
    analyses = [tariff_engine.calculate_landed_cost(s) for s in shipments]
    return success_response(
        {
            "shipments_analyzed": len(analyses),
            "total_tariff_exposure_usd": sum(a["tariff_amount_usd"] for a in analyses),
            "total_landed_cost_usd": sum(a["total_landed_cost_usd"] for a in analyses),
            "high_tariff_shipments": len([a for a in analyses if a["tariff_flag"]]),
            "cbam_applicable_shipments": len([a for a in analyses if a["cbam_applicable"]]),
        }
    )
