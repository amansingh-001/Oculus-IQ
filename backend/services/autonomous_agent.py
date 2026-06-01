"""Autonomous Agent — proactive supply chain monitoring service."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Shipment
from services.risk_engine import RiskEngine
from services.weather_service import get_weather_risk


class AutonomousAgentService:
    """
    When enabled, continuously monitors the supply chain and takes proactive actions.
    """

    def __init__(self) -> None:
        self.is_active = False
        self.agent_log: list[dict[str, Any]] = []
        self.last_cycle_at: str | None = None
        self.actions_today: int = 0

    async def run_agent_cycle(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Called periodically by APScheduler when agent is active."""
        if not self.is_active:
            return []

        risk_engine = RiskEngine()
        actions_taken: list[dict[str, Any]] = []

        # Check 1: Weather-triggered risk updates
        result = await db.execute(
            select(Shipment).where(Shipment.status == "in_transit").limit(50)
        )
        in_transit = result.scalars().all()

        for ship in in_transit:
            try:
                weather = await get_weather_risk(ship.current_lat, ship.current_lon)
                new_risk = risk_engine.calculate_risk(ship, weather)
                risk_diff = abs(new_risk["risk_score"] - ship.risk_score)

                if risk_diff > 10:
                    old_score = ship.risk_score
                    ship.risk_score = new_risk["risk_score"]
                    ship.risk_level = new_risk["risk_level"]
                    ship.risk_factors = new_risk["risk_factors"]
                    ship.last_updated = datetime.utcnow()

                    action = {
                        "action": "risk_updated",
                        "shipment_id": ship.id,
                        "reason": (
                            f"Risk score changed significantly: "
                            f"{old_score} → {new_risk['risk_score']}"
                        ),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }

                    if new_risk["risk_score"] >= 75 and old_score < 75:
                        action["action"] = "alert_threshold_crossed"
                        action["reason"] = (
                            f"Risk crossed critical threshold: "
                            f"{old_score} → {new_risk['risk_score']}"
                        )

                    actions_taken.append(action)
            except Exception as exc:
                print(f"Agent: error processing {ship.id}: {exc}")

        if actions_taken:
            await db.commit()

        # Log the cycle
        self.last_cycle_at = datetime.utcnow().isoformat() + "Z"
        self.actions_today += len(actions_taken)

        self.agent_log.append({
            "cycle_at": self.last_cycle_at,
            "actions_count": len(actions_taken),
            "actions": actions_taken,
        })

        # Keep only last 50 cycles
        if len(self.agent_log) > 50:
            self.agent_log = self.agent_log[-50:]

        return actions_taken

    def get_status(self) -> dict[str, Any]:
        return {
            "is_active": self.is_active,
            "last_cycle_at": self.last_cycle_at,
            "actions_today": self.actions_today,
            "agent_log": self.agent_log[-10:],
        }

    def toggle(self) -> dict[str, Any]:
        self.is_active = not self.is_active
        return {
            "is_active": self.is_active,
            "message": "Autonomous agent activated" if self.is_active else "Autonomous agent deactivated",
        }

    def get_log(self) -> list[dict[str, Any]]:
        return self.agent_log


autonomous_agent = AutonomousAgentService()
