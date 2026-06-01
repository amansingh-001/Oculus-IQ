from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Disruption, Shipment
from services.gemini_service import gemini_service


router = APIRouter()


@router.get("/feeds")
async def feeds_health(db: AsyncSession = Depends(get_db)):
    disruptions_last = await db.scalar(select(func.max(Disruption.last_updated)))
    shipments_counts = await db.execute(select(Shipment.source, func.count()).group_by(Shipment.source))
    shipments_by_source = {row[0]: row[1] for row in shipments_counts.all()}
    sources = sorted(shipments_by_source.keys())
    status_parts = ["synthetic" if source == "seed" else source for source in sources]

    return success_response(
        {
            "feeds": {
                "weather": {
                    "status": "live",
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                    "provider": "Open-Meteo",
                },
                "disruptions": {
                    "status": "live",
                    "last_updated": (disruptions_last.isoformat() + "Z") if disruptions_last else None,
                    "provider": "GDELT",
                },
                "shipments": {
                    "status": "+".join(status_parts) if status_parts else "unknown",
                    "csv_count": shipments_by_source.get("csv", 0),
                    "synthetic_count": shipments_by_source.get("seed", 0),
                },
                "gemini": {
                    "status": "active" if gemini_service.is_configured else "inactive",
                    "model": gemini_service.model_name,
                    "key_configured": gemini_service.is_configured,
                },
            }
        }
    )
