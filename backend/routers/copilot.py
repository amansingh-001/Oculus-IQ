from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Alert, Client, Disruption, Shipment
from routers.serializers import serialize_shipment
from services.gemini_service import gemini_service
from services.sla_service import sla_predictor


router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_history: list[ChatMessage] = Field(default_factory=list)


@router.post("/chat")
async def copilot_chat(payload: CopilotChatRequest, db: AsyncSession = Depends(get_db)):
    shipment_result = await db.execute(select(Shipment))
    shipments = shipment_result.scalars().all()

    total = len(shipments)
    critical = [s for s in shipments if s.risk_level == "critical"]
    high = [s for s in shipments if s.risk_level == "high"]
    medium = [s for s in shipments if s.risk_level == "medium"]
    low = [s for s in shipments if s.risk_level == "low"]

    disruption_result = await db.execute(
        select(Disruption).where(Disruption.active.is_(True)).order_by(Disruption.detected_at.desc()).limit(5)
    )
    disruptions = disruption_result.scalars().all()

    client_result = await db.execute(select(Client))
    clients = client_result.scalars().all()
    sla_risks = []
    for client in clients:
        client_shipments = [s for s in shipments if s.client_id == client.id]
        status = sla_predictor.check_client_sla_risk(client, client_shipments)
        if status.get("status") in {"breach_likely", "breach_risk"}:
            sla_risks.append(status)

    pending_alerts = int(
        (
            await db.scalar(
                select(func.count()).select_from(Alert).where(Alert.acknowledged.is_(False))
            )
        )
        or 0
    )

    top_critical = sorted(critical, key=lambda x: x.risk_score, reverse=True)[:5]
    critical_summaries = [
        f"{s.id}: {s.origin_city}→{s.dest_city}, risk={s.risk_score}, carrier={s.carrier}"
        for s in top_critical
    ]

    # Interpret as up to 10 turns (5 user + 5 assistant).
    history = payload.conversation_history[-10:]

    context = {
        "stats": {
            "total": total,
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
        },
        "active_disruptions": len(disruptions),
        "active_disruption_titles": [d.title for d in disruptions],
        "critical_shipments": critical_summaries,
        "pending_alerts": pending_alerts,
        "total_clients": len(clients),
        "clients_at_sla_risk": [
            f"{item['client_name']} ({item['status']}, {item['at_risk_shipments']} shipments)"
            for item in sla_risks[:8]
        ],
        "highest_risk_client": sla_risks[0]["client_name"] if sla_risks else "None",
        "total_cargo_under_management_usd": sum(float(c.total_cargo_value_annual_usd or 0) for c in clients),
    }

    response_text = await gemini_service.copilot_chat(
        payload.message,
        context,
        history=[m.model_dump() for m in history],
    )

    return success_response(
        {
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )
