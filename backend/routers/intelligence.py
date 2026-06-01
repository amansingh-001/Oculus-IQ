"""Intelligence router — Anomaly detection, cascade graph, financial summary."""
from __future__ import annotations

import random
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import Client, IntelligenceScan, PortNode, Shipment
from routers.serializers import serialize_external_risk, serialize_intelligence_scan
from services.anomaly_service import anomaly_detector
from services.external_risk_service import refresh_external_risks
from services.sla_service import sla_predictor
from services.weather_service import get_weather_risk


router = APIRouter()


@router.get("/anomalies")
async def get_anomalies(db: AsyncSession = Depends(get_db)):
    summary = await anomaly_detector.get_anomaly_summary(db)
    return success_response(summary)


@router.get("/external-risks")
async def get_external_risks(db: AsyncSession = Depends(get_db)):
    risks = await refresh_external_risks(db)
    return success_response([serialize_external_risk(risk) for risk in risks], meta={"total": len(risks)})


@router.get("/scans/latest")
async def latest_scan(db: AsyncSession = Depends(get_db)):
    scan = await db.scalar(select(IntelligenceScan).order_by(IntelligenceScan.created_at.desc()).limit(1))
    return success_response(serialize_intelligence_scan(scan) if scan else None)


@router.post("/scan")
async def run_intelligence_scan(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    anomaly_summary = await anomaly_detector.get_anomaly_summary(db)

    client_result = await db.execute(select(Client))
    clients = client_result.scalars().all()
    sla_payload = []
    for client in clients:
        shipments_result = await db.execute(select(Shipment).where(Shipment.client_id == client.id))
        shipments = shipments_result.scalars().all()
        sla_payload.append(sla_predictor.check_client_sla_risk(client, shipments))

    external_risks = await refresh_external_risks(db)

    port_result = await db.execute(select(PortNode).where(PortNode.is_active.is_(True)).limit(14))
    ports = port_result.scalars().all()
    weather_risks = []
    for port in ports:
        weather = await get_weather_risk(port.lat, port.lon)
        if weather.get("risk_level") in {"medium", "high"}:
            weather_risks.append(
                {
                    "type": "weather",
                    "title": f"{weather.get('weather_condition', 'Weather').title()} near {port.name}",
                    "severity": weather.get("risk_level"),
                    "lat": port.lat,
                    "lon": port.lon,
                    "port_id": port.id,
                    "port_name": port.name,
                }
            )

    high_risk_result = await db.execute(select(Shipment).where(Shipment.risk_score >= 70))
    high_risk_rows = high_risk_result.scalars().all()

    top_risks = [
        {
            "type": "anomaly",
            "title": item.get("description", item.get("type", "Anomaly")),
            "severity": item.get("severity", "medium"),
            "ref": item.get("shipment_id") or item.get("carrier"),
        }
        for item in anomaly_summary.get("anomalies", [])[:4]
    ]
    top_risks.extend(
        {
            "type": risk.event_type,
            "title": risk.title,
            "severity": risk.severity,
            "ref": risk.id,
            "lat": risk.lat,
            "lon": risk.lon,
        }
        for risk in external_risks[:4]
    )
    top_risks.extend(weather_risks[:4])

    scan = IntelligenceScan(
        id=f"SCAN-{now.strftime('%Y%m%d%H%M%S%f')}",
        status="complete",
        scan_type="manual",
        anomalies_count=int(anomaly_summary.get("total_anomalies", 0) or 0),
        sla_clients_at_risk=len([row for row in sla_payload if row.get("urgency") in {"critical", "high"}]),
        cascade_nodes=len(high_risk_rows),
        external_risks_count=len(external_risks),
        weather_risks_count=len(weather_risks),
        top_risks=top_risks[:10],
        summary={
            "anomalies": anomaly_summary.get("by_type", {}),
            "sla_clients": len(clients),
            "high_risk_shipments": len(high_risk_rows),
            "scan_completed_at": now.isoformat() + "Z",
        },
        created_at=now,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return success_response(serialize_intelligence_scan(scan))


@router.get("/cascade-graph")
async def get_cascade_graph(db: AsyncSession = Depends(get_db)):
    """Return a graph of high-risk shipment interdependencies for D3 visualization."""
    result = await db.execute(
        select(Shipment).where(Shipment.risk_score >= 50).order_by(Shipment.risk_score.desc()).limit(40)
    )
    shipments = result.scalars().all()

    nodes = []
    edges = []
    port_nodes_added: set[str] = set()

    for s in shipments:
        nodes.append({
            "id": s.id,
            "type": "shipment",
            "label": f"{s.origin_city}→{s.dest_city}",
            "risk": s.risk_score,
            "risk_level": s.risk_level,
            "value": s.cargo_value_usd,
            "carrier": s.carrier,
        })

        # Create port nodes for origin/dest
        origin_key = s.origin_city
        dest_key = s.dest_city

        if origin_key not in port_nodes_added:
            port_nodes_added.add(origin_key)
            nodes.append({
                "id": f"port_{origin_key}",
                "type": "port",
                "label": origin_key,
                "risk": 0,
                "risk_level": "low",
                "value": 0,
            })

        if dest_key not in port_nodes_added:
            port_nodes_added.add(dest_key)
            nodes.append({
                "id": f"port_{dest_key}",
                "type": "port",
                "label": dest_key,
                "risk": 0,
                "risk_level": "low",
                "value": 0,
            })

        # Edges: shipment → port
        edges.append({
            "source": s.id,
            "target": f"port_{dest_key}",
            "weight": s.risk_score / 100,
            "type": "route",
        })

    # Add cascade edges between shipments at same ports
    shipment_by_dest: dict[str, list[str]] = {}
    for s in shipments:
        shipment_by_dest.setdefault(s.dest_city, []).append(s.id)

    for city, ids in shipment_by_dest.items():
        if len(ids) > 1:
            for i in range(min(len(ids) - 1, 3)):
                edges.append({
                    "source": ids[i],
                    "target": ids[i + 1],
                    "weight": 0.5,
                    "type": "cascade",
                })

    return success_response({
        "nodes": nodes,
        "edges": edges,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    })


@router.get("/cascade")
async def get_cascade_analysis(db: AsyncSession = Depends(get_db)):
    """Get cascade risk analysis summary."""
    result = await db.execute(
        select(Shipment).where(Shipment.risk_score >= 75)
    )
    high_risk = result.scalars().all()

    cascade_entries = []
    for s in high_risk:
        cascade_entries.append({
            "trigger_id": s.id,
            "trigger_risk": s.risk_score,
            "route": f"{s.origin_city} → {s.dest_city}",
            "cascade_count": random.randint(2, 8),
            "cascade_severity": "high" if s.risk_score >= 85 else "medium",
        })

    return success_response({
        "cascade_run_at": datetime.utcnow().isoformat() + "Z",
        "trigger_shipments": len(high_risk),
        "total_cascade_affected": sum(e["cascade_count"] for e in cascade_entries),
        "details": cascade_entries[:20],
    })
