"""Port congestion simulation engine."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import PortNode


class PortCongestionEngine:
    """
    Simulates real-world port congestion patterns based on:
    - Time of day (peak hours)
    - Active disruptions affecting the port region
    - Random stochastic noise
    """

    BASE_CONGESTION: dict[str, float] = {
        "CNSHA": 72, "SGSIN": 58, "NLRTM": 61, "DEHAM": 55, "USLA": 67,
        "AEJEA": 49, "INMAA": 44, "INNSAV": 52, "TRIST": 38, "GBFXT": 42,
        "AUSYD": 35, "JPTYO": 48, "KRPUS": 56, "CNSZN": 68, "USNYC": 53,
        "BEANR": 59, "MYPKG": 46, "SUEZ_CANAL": 65, "STRAIT_MALACCA": 50,
        "STRAIT_HORMUZ": 40, "PANAMA_CANAL": 55, "CAPE_GOOD_HOPE": 30,
        "HKGHK": 42, "AEDXB": 38, "USJFK": 45, "DEFRA": 40, "SGCHN": 36,
    }

    def get_port_congestion(self, port_id: str, active_disruptions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        base = self.BASE_CONGESTION.get(port_id, 50)
        active_disruptions = active_disruptions or []

        # Time-of-day factor
        hour = datetime.utcnow().hour
        time_factor = 1.2 if 6 <= hour <= 22 else 0.8

        # Disruption impact
        disruption_factor = 1.0
        for d in active_disruptions:
            affected = d.get("affected_ports", [])
            if port_id in affected:
                sev = d.get("severity_score", 70)
                disruption_factor += 0.3 * (sev / 100)

        # Stochastic noise ±15%
        noise = random.uniform(0.85, 1.15)

        final_score = min(100, base * time_factor * disruption_factor * noise)
        wait_hours = (final_score / 100) * 72

        if final_score > 80:
            status = "critical"
        elif final_score > 60:
            status = "high"
        elif final_score > 40:
            status = "elevated"
        else:
            status = "normal"

        return {
            "port_id": port_id,
            "congestion_score": round(final_score, 1),
            "wait_hours_estimated": round(wait_hours, 1),
            "status": status,
            "trend": "increasing" if noise > 1.05 else "decreasing" if noise < 0.95 else "stable",
            "source": "simulated",
            "reliability": 0.55,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

    async def get_all_port_congestion(self, db: AsyncSession) -> list[dict[str, Any]]:
        results = []
        for port_id in self.BASE_CONGESTION:
            congestion = self.get_port_congestion(port_id)
            results.append(congestion)
            # Update DB
            await db.execute(
                update(PortNode)
                .where(PortNode.id == port_id)
                .values(
                    congestion_score=congestion["congestion_score"],
                    avg_wait_hours=congestion["wait_hours_estimated"],
                    last_updated=datetime.utcnow(),
                )
            )
        await db.commit()
        return results


port_congestion_engine = PortCongestionEngine()
