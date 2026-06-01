"""Simulation router — Digital Twin API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from services.simulation_engine import simulation_engine


router = APIRouter()


class RunSimulationRequest(BaseModel):
    scenario_key: str = Field(min_length=1)
    duration_hours: int = Field(default=48, ge=1, le=8760)
    target_type: str = "all"
    client_id: str | None = None
    shipment_id: str | None = None
    operator_name: str | None = None
    severity: str | None = None
    region: str | None = None


@router.get("/scenarios")
async def list_scenarios():
    scenarios = await simulation_engine.get_scenarios()
    return success_response(scenarios, meta={"total": len(scenarios)})


@router.post("/run")
async def run_simulation(payload: RunSimulationRequest, db: AsyncSession = Depends(get_db)):
    result = await simulation_engine.run_simulation(
        payload.scenario_key,
        payload.duration_hours,
        db,
        target={
            "target_type": payload.target_type,
            "client_id": payload.client_id,
            "shipment_id": payload.shipment_id,
            "operator_name": payload.operator_name,
            "severity": payload.severity,
            "region": payload.region,
        },
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return success_response(result)


@router.get("/history")
async def simulation_history(db: AsyncSession = Depends(get_db)):
    history = await simulation_engine.get_history(db)
    return success_response(history, meta={"total": len(history)})


@router.get("/{sim_id}")
async def get_simulation(sim_id: str, db: AsyncSession = Depends(get_db)):
    result = await simulation_engine.get_simulation(sim_id, db)
    if not result:
        raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
    return success_response(result)
