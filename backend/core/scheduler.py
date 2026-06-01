from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import Shipment
from services.risk_engine import RiskEngine
from services.weather_service import get_weather_risk


scheduler = AsyncIOScheduler(timezone="UTC")
_risk_engine = RiskEngine()


async def refresh_risk_scores() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Shipment).where(Shipment.status == "in_transit"))
        shipments = result.scalars().all()

        for shipment in shipments:
            weather = await get_weather_risk(shipment.current_lat, shipment.current_lon)
            risk = _risk_engine.calculate_risk(shipment, weather)
            shipment.risk_score = risk["risk_score"]
            shipment.risk_level = risk["risk_level"]
            shipment.risk_factors = risk["risk_factors"]
            shipment.last_updated = datetime.utcnow()

        await session.commit()


async def update_port_congestion() -> None:
    """Update congestion scores for all ports."""
    from services.port_service import port_congestion_engine
    async with AsyncSessionLocal() as session:
        await port_congestion_engine.get_all_port_congestion(session)


async def run_agent_cycle() -> None:
    """Run autonomous agent cycle if enabled."""
    from services.autonomous_agent import autonomous_agent
    if not autonomous_agent.is_active:
        return
    async with AsyncSessionLocal() as session:
        await autonomous_agent.run_agent_cycle(session)


async def ingest_gdelt_news() -> None:
    from services.gdelt_service import ingest_gdelt_disruptions
    async with AsyncSessionLocal() as session:
        await ingest_gdelt_disruptions(session)


def start_scheduler() -> None:
    if scheduler.get_job("refresh_risk_scores") is None:
        scheduler.add_job(
            refresh_risk_scores,
            trigger="interval",
            minutes=5,
            id="refresh_risk_scores",
            max_instances=1,
            coalesce=True,
        )

    if scheduler.get_job("port_congestion") is None:
        scheduler.add_job(
            update_port_congestion,
            trigger="interval",
            minutes=15,
            id="port_congestion",
            max_instances=1,
            coalesce=True,
        )

    if scheduler.get_job("agent_cycle") is None:
        scheduler.add_job(
            run_agent_cycle,
            trigger="interval",
            minutes=10,
            id="agent_cycle",
            max_instances=1,
            coalesce=True,
        )

    if scheduler.get_job("gdelt_ingest") is None:
        scheduler.add_job(
            ingest_gdelt_news,
            trigger="interval",
            minutes=30,
            id="gdelt_ingest",
            max_instances=1,
            coalesce=True,
        )

    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
