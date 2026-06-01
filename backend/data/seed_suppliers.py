"""Seed data for supplier profiles."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from models import SupplierProfile


SUPPLIERS = [
    {"id": "SUP-001", "name": "Foxconn Taiwan", "country": "Taiwan", "industry": "Electronics",
     "risk_score": 72, "on_time_rate": 94.2, "avg_lead_time_days": 14,
     "alternatives": ["SUP-002", "SUP-003"], "geo_risk": 65, "stability": "stable", "shipments": 42},
    {"id": "SUP-002", "name": "Samsung SDI", "country": "South Korea", "industry": "Electronics",
     "risk_score": 81, "on_time_rate": 96.1, "avg_lead_time_days": 12,
     "alternatives": ["SUP-001", "SUP-005"], "geo_risk": 45, "stability": "stable", "shipments": 38},
    {"id": "SUP-003", "name": "BYD Electronic", "country": "China", "industry": "Electronics",
     "risk_score": 58, "on_time_rate": 88.7, "avg_lead_time_days": 18,
     "alternatives": ["SUP-001"], "geo_risk": 72, "stability": "watch", "shipments": 55},
    {"id": "SUP-004", "name": "Cipla Pharma", "country": "India", "industry": "Pharmaceuticals",
     "risk_score": 76, "on_time_rate": 91.3, "avg_lead_time_days": 21,
     "alternatives": ["SUP-006", "SUP-007"], "geo_risk": 55, "stability": "stable", "shipments": 28},
    {"id": "SUP-005", "name": "TSMC", "country": "Taiwan", "industry": "Electronics",
     "risk_score": 85, "on_time_rate": 97.8, "avg_lead_time_days": 10,
     "alternatives": ["SUP-002"], "geo_risk": 65, "stability": "stable", "shipments": 60},
    {"id": "SUP-006", "name": "Novartis India", "country": "India", "industry": "Pharmaceuticals",
     "risk_score": 70, "on_time_rate": 89.5, "avg_lead_time_days": 24,
     "alternatives": ["SUP-004"], "geo_risk": 55, "stability": "stable", "shipments": 22},
    {"id": "SUP-007", "name": "Roche Basel", "country": "Switzerland", "industry": "Pharmaceuticals",
     "risk_score": 92, "on_time_rate": 98.1, "avg_lead_time_days": 8,
     "alternatives": ["SUP-004", "SUP-006"], "geo_risk": 15, "stability": "stable", "shipments": 18},
    {"id": "SUP-008", "name": "Bosch Automotive", "country": "Germany", "industry": "Automotive Parts",
     "risk_score": 88, "on_time_rate": 95.6, "avg_lead_time_days": 11,
     "alternatives": ["SUP-009", "SUP-010"], "geo_risk": 20, "stability": "stable", "shipments": 35},
    {"id": "SUP-009", "name": "Denso Corp", "country": "Japan", "industry": "Automotive Parts",
     "risk_score": 82, "on_time_rate": 96.4, "avg_lead_time_days": 13,
     "alternatives": ["SUP-008"], "geo_risk": 30, "stability": "stable", "shipments": 30},
    {"id": "SUP-010", "name": "ZF Friedrichshafen", "country": "Germany", "industry": "Automotive Parts",
     "risk_score": 79, "on_time_rate": 93.8, "avg_lead_time_days": 12,
     "alternatives": ["SUP-008", "SUP-009"], "geo_risk": 20, "stability": "stable", "shipments": 25},
    {"id": "SUP-011", "name": "BASF Chemicals", "country": "Germany", "industry": "Chemicals",
     "risk_score": 84, "on_time_rate": 94.0, "avg_lead_time_days": 15,
     "alternatives": ["SUP-012"], "geo_risk": 20, "stability": "stable", "shipments": 40},
    {"id": "SUP-012", "name": "Sinopec Chemical", "country": "China", "industry": "Chemicals",
     "risk_score": 45, "on_time_rate": 82.3, "avg_lead_time_days": 22,
     "alternatives": ["SUP-011"], "geo_risk": 72, "stability": "watch", "shipments": 48},
    {"id": "SUP-013", "name": "Arvind Textiles", "country": "India", "industry": "Textiles",
     "risk_score": 62, "on_time_rate": 86.1, "avg_lead_time_days": 20,
     "alternatives": ["SUP-014"], "geo_risk": 55, "stability": "stable", "shipments": 32},
    {"id": "SUP-014", "name": "Li & Fung Trading", "country": "Hong Kong", "industry": "Textiles",
     "risk_score": 55, "on_time_rate": 84.9, "avg_lead_time_days": 25,
     "alternatives": ["SUP-013", "SUP-015"], "geo_risk": 60, "stability": "watch", "shipments": 45},
    {"id": "SUP-015", "name": "Cargill Foods", "country": "USA", "industry": "Food",
     "risk_score": 90, "on_time_rate": 97.2, "avg_lead_time_days": 7,
     "alternatives": [], "geo_risk": 10, "stability": "stable", "shipments": 20},
]


async def seed_suppliers() -> None:
    """Seed supplier profiles if they don't exist yet."""
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(SupplierProfile))
        if existing and existing > 0:
            return

        for s in SUPPLIERS:
            incident_date = datetime.utcnow() - timedelta(days=30) if s["risk_score"] < 60 else None
            session.add(SupplierProfile(
                id=s["id"],
                name=s["name"],
                country=s["country"],
                industry=s["industry"],
                risk_score=float(s["risk_score"]),
                on_time_rate=float(s["on_time_rate"]),
                avg_lead_time_days=float(s["avg_lead_time_days"]),
                alternative_supplier_ids=s["alternatives"],
                geopolitical_risk=float(s["geo_risk"]),
                financial_stability=s["stability"],
                active_shipments_count=s["shipments"],
                last_incident_date=incident_date,
            ))

        await session.commit()
