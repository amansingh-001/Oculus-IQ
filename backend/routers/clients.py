from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Client, Shipment
from routers.serializers import serialize_client, serialize_shipment
from services.notification_service import notification_service
from services.sla_service import sla_predictor


router = APIRouter()


class CreateClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    sla_on_time_pct: float = Field(ge=0, le=100)
    primary_contact: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    risk_tolerance: str = "medium"
    annual_shipment_count: int = 0
    total_cargo_value_annual_usd: float = 0
    notes: str | None = None


async def _client_shipments(db: AsyncSession, client_id: str) -> list[Shipment]:
    result = await db.execute(select(Shipment).where(Shipment.client_id == client_id))
    return result.scalars().all()


async def _client_with_status(db: AsyncSession, client: Client) -> dict:
    shipments = await _client_shipments(db, client.id)
    sla = sla_predictor.check_client_sla_risk(client, shipments)
    active = [s for s in shipments if s.status in {"in_transit", "pending", "delayed"}]
    cargo_active = sum(float(s.cargo_value_usd or 0) for s in active)
    return serialize_client(
        client,
        {
            "sla_status": sla,
            "active_shipments_count": len(active),
            "at_risk_shipments_count": len([s for s in shipments if s.risk_score >= 60]),
            "active_cargo_value_usd": round(cargo_active),
        },
    )


@router.get("")
async def list_clients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).order_by(Client.name))
    clients = result.scalars().all()
    payload = [await _client_with_status(db, client) for client in clients]
    return success_response(payload, meta={"total": len(payload)})


@router.post("")
async def create_client(payload: CreateClientRequest, db: AsyncSession = Depends(get_db)):
    last_id = await db.scalar(select(Client.id).order_by(Client.id.desc()).limit(1))
    next_num = int(last_id.split("-")[1]) + 1 if last_id else 1
    client = Client(
        id=f"CLT-{next_num:03d}",
        name=payload.name,
        industry=payload.industry,
        country=payload.country,
        city=payload.city,
        primary_contact=payload.primary_contact,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        annual_shipment_count=payload.annual_shipment_count,
        total_cargo_value_annual_usd=payload.total_cargo_value_annual_usd,
        risk_tolerance=payload.risk_tolerance,
        sla_on_time_pct=payload.sla_on_time_pct,
        current_sla_performance=payload.sla_on_time_pct,
        active_shipments_count=0,
        at_risk_shipments_count=0,
        created_at=datetime.utcnow(),
        notes=payload.notes,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return success_response(serialize_client(client))


@router.get("/sla-overview")
async def sla_overview(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).order_by(Client.name))
    clients = result.scalars().all()
    payload = []
    for client in clients:
        shipments = await _client_shipments(db, client.id)
        sla = sla_predictor.check_client_sla_risk(client, shipments)
        payload.append(
            {
                **sla,
                "client_id": client.id,
                "client_name": client.name,
                "industry": client.industry,
                "city": client.city,
                "country": client.country,
                "contact_phone": client.contact_phone,
                "active_cargo_value_usd": round(sum(float(s.cargo_value_usd or 0) for s in shipments)),
            }
        )

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    payload.sort(key=lambda item: (order.get(item.get("urgency"), 9), -item.get("at_risk_shipments", 0)))
    return success_response(payload, meta={"total": len(payload)})


@router.get("/{client_id}")
async def client_detail(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return success_response(await _client_with_status(db, client))


@router.get("/{client_id}/shipments")
async def client_shipments(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    shipments = await _client_shipments(db, client_id)
    shipments = sorted(shipments, key=lambda s: s.risk_score, reverse=True)
    return success_response([serialize_shipment(s) for s in shipments], meta={"total": len(shipments)})


@router.get("/{client_id}/sla-status")
async def client_sla_status(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return success_response(sla_predictor.check_client_sla_risk(client, await _client_shipments(db, client_id)))


@router.get("/{client_id}/weekly-report")
async def client_weekly_report(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return success_response(notification_service.generate_client_weekly_report(client, await _client_shipments(db, client_id)))


@router.get("/{client_id}/whatsapp-alert")
async def client_whatsapp_alert(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    shipments = await _client_shipments(db, client_id)
    top_risk = sorted(shipments, key=lambda s: s.risk_score, reverse=True)
    if not top_risk:
        return success_response({"message": "No active shipments for this client.", "phone": client.contact_phone})
    return success_response(
        {
            "phone": client.contact_phone,
            "shipment_id": top_risk[0].id,
            "message": notification_service.generate_whatsapp_alert(top_risk[0]),
        }
    )
