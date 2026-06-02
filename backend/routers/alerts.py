from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Alert, Disruption, Shipment
from routers.serializers import serialize_alert
from services.alert_service import (
    build_alert_summary,
    build_alert_title,
    build_recommended_actions,
    priority_for_risk,
    should_generate_alert,
)
from services.gemini_service import gemini_service


router = APIRouter()
_priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


@router.get("")
async def list_alerts(
    acknowledged: bool | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Alert)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged == acknowledged)
    if priority:
        stmt = stmt.where(Alert.priority == priority)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    rows = sorted(rows, key=lambda item: (_priority_order.get(item.priority, 9), item.created_at), reverse=False)

    return success_response([serialize_alert(row) for row in rows], meta={"total": len(rows)})


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.last_updated = datetime.utcnow()
    await db.commit()

    return success_response({"id": alert.id, "acknowledged": True})


@router.get("/{alert_id}/draft")
async def alert_draft(alert_id: str, db: AsyncSession = Depends(get_db)):
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    draft = await gemini_service.draft_alert_notification(
        {
            "alert_id": alert.id,
            "shipment_id": alert.shipment_id,
            "title": alert.title,
            "summary": alert.ai_summary,
            "recommended_actions": alert.recommended_actions,
        }
    )

    alert.drafted_notification = draft.get("body")
    alert.last_updated = datetime.utcnow()
    await db.commit()

    return success_response(draft)


@router.post("/generate")
async def generate_alerts(db: AsyncSession = Depends(get_db)):
    shipment_result = await db.execute(
        select(Shipment).where(Shipment.risk_level.in_(["high", "critical"]))
    )
    shipments = shipment_result.scalars().all()

    disruption_result = await db.execute(
        select(Disruption).where(and_(Disruption.active.is_(True), Disruption.severity.in_(["high", "critical"])))
    )
    disruptions = disruption_result.scalars().all()

    created = 0
    last_alert_id = await db.scalar(select(Alert.id).order_by(Alert.id.desc()).limit(1))
    next_alert_num = int(last_alert_id.split("-")[1]) + 1 if last_alert_id else 1

    for shipment in shipments:
        disruption = next((d for d in disruptions if shipment.id in (d.affected_shipments or [])), None)
        severity = disruption.severity if disruption else "high"

        if not should_generate_alert(shipment.risk_score, shipment.cargo_value_usd, severity):
            continue

        existing = await db.scalar(
            select(Alert).where(
                Alert.shipment_id == shipment.id,
                Alert.disruption_id == (disruption.id if disruption else None),
                Alert.acknowledged.is_(False),
            )
        )
        if existing is not None:
            continue

        alert = Alert(
            id=f"ALT-{next_alert_num:04d}",
            shipment_id=shipment.id,
            disruption_id=disruption.id if disruption else None,
            priority=priority_for_risk(shipment.risk_score),
            title=build_alert_title(shipment.id, shipment.risk_level),
            ai_summary=build_alert_summary(shipment, disruption),
            drafted_notification=None,
            recommended_actions=build_recommended_actions(shipment.mode, shipment.risk_level),
            created_at=datetime.utcnow(),
            acknowledged=False,
            source="system",
            reliability=0.7,
            last_updated=datetime.utcnow(),
        )
        db.add(alert)
        created += 1
        next_alert_num += 1

    await db.commit()

    return success_response({"created_count": created})
