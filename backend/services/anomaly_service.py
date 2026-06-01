"""Anomaly detection service — statistical methods, no ML libraries needed."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Shipment
from routers.serializers import serialize_shipment


class AnomalyDetector:
    """Detects unusual patterns in shipment data using Z-score and moving averages."""

    async def detect_anomalies(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await db.execute(select(Shipment))
        shipments_raw = result.scalars().all()
        shipments = [serialize_shipment(s) for s in shipments_raw]

        anomalies: list[dict[str, Any]] = []

        # Anomaly Type 1: Unusual risk score spike (Z-score)
        in_transit = [s for s in shipments if s["status"] == "in_transit"]
        if in_transit:
            risk_scores = [s["risk_score"] for s in in_transit]
            mean_risk = sum(risk_scores) / len(risk_scores)
            std_risk = (sum((r - mean_risk) ** 2 for r in risk_scores) / len(risk_scores)) ** 0.5

            for ship in in_transit:
                z_score = (ship["risk_score"] - mean_risk) / (std_risk + 0.001)
                if z_score > 2.5:
                    anomalies.append({
                        "type": "risk_spike",
                        "shipment_id": ship["id"],
                        "severity": "high",
                        "description": (
                            f"Risk score {ship['risk_score']} is {z_score:.1f}σ above "
                            f"fleet average ({mean_risk:.0f})"
                        ),
                        "value": ship["risk_score"],
                        "threshold": round(mean_risk + 2.5 * std_risk, 1),
                        "detected_at": datetime.utcnow().isoformat() + "Z",
                    })

        # Anomaly Type 2: Silent delays (ETA passed but status not updated)
        now = datetime.now(timezone.utc)
        for ship in shipments:
            if ship["status"] == "in_transit" and ship.get("eta"):
                try:
                    eta_str = ship["eta"].replace("Z", "+00:00")
                    eta = datetime.fromisoformat(eta_str)
                    if eta.tzinfo is None:
                        eta = eta.replace(tzinfo=timezone.utc)
                    days_overdue = (now - eta).days
                    if days_overdue > 0:
                        anomalies.append({
                            "type": "silent_delay",
                            "shipment_id": ship["id"],
                            "severity": "critical" if days_overdue > 3 else "high",
                            "description": (
                                f"ETA passed {days_overdue} day(s) ago but status still "
                                f"'in_transit' — possible tracking gap"
                            ),
                            "value": days_overdue,
                            "detected_at": datetime.utcnow().isoformat() + "Z",
                        })
                except (ValueError, TypeError):
                    pass

        # Anomaly Type 3: Carrier cluster failures
        carrier_counts: dict[str, int] = {}
        carrier_delays: dict[str, int] = {}
        for ship in shipments:
            carrier = ship["carrier"]
            carrier_counts[carrier] = carrier_counts.get(carrier, 0) + 1
            if ship["status"] == "delayed":
                carrier_delays[carrier] = carrier_delays.get(carrier, 0) + 1

        for carrier, delay_count in carrier_delays.items():
            total = carrier_counts.get(carrier, 1)
            rate = delay_count / total
            if rate > 0.35 and delay_count >= 3:
                anomalies.append({
                    "type": "carrier_cluster_failure",
                    "carrier": carrier,
                    "severity": "high" if rate > 0.5 else "medium",
                    "description": (
                        f"{carrier}: {rate * 100:.0f}% of shipments delayed "
                        f"({delay_count}/{total}) — possible operational crisis"
                    ),
                    "value": round(rate * 100, 1),
                    "detected_at": datetime.utcnow().isoformat() + "Z",
                })

        return anomalies

    async def get_anomaly_summary(self, db: AsyncSession) -> dict[str, Any]:
        anomalies = await self.detect_anomalies(db)
        return {
            "total_anomalies": len(anomalies),
            "by_type": {
                "risk_spikes": len([a for a in anomalies if a["type"] == "risk_spike"]),
                "silent_delays": len([a for a in anomalies if a["type"] == "silent_delay"]),
                "carrier_failures": len([a for a in anomalies if a["type"] == "carrier_cluster_failure"]),
            },
            "anomalies": anomalies,
            "scan_time": datetime.utcnow().isoformat() + "Z",
        }


anomaly_detector = AnomalyDetector()
