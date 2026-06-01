"""Suppliers router — Supplier resilience scoring and profiles."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.responses import success_response
from models import SupplierProfile


router = APIRouter()


def _serialize_supplier(s: SupplierProfile) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "country": s.country,
        "industry": s.industry,
        "risk_score": s.risk_score,
        "on_time_rate": s.on_time_rate,
        "avg_lead_time_days": s.avg_lead_time_days,
        "alternative_supplier_ids": s.alternative_supplier_ids,
        "geopolitical_risk": s.geopolitical_risk,
        "financial_stability": s.financial_stability,
        "active_shipments_count": s.active_shipments_count,
        "last_incident_date": s.last_incident_date.isoformat() + "Z" if s.last_incident_date else None,
    }


@router.get("")
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SupplierProfile).order_by(SupplierProfile.risk_score.desc()))
    suppliers = result.scalars().all()
    return success_response(
        [_serialize_supplier(s) for s in suppliers],
        meta={"total": len(suppliers)},
    )


@router.get("/at-risk")
async def at_risk_suppliers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SupplierProfile).where(SupplierProfile.risk_score < 60)
    )
    suppliers = result.scalars().all()
    return success_response(
        [_serialize_supplier(s) for s in suppliers],
        meta={"total": len(suppliers)},
    )


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(SupplierProfile, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return success_response(_serialize_supplier(supplier))


@router.get("/{supplier_id}/scorecard")
async def supplier_scorecard(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(SupplierProfile, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

    # Build scorecard
    scorecard = {
        **_serialize_supplier(supplier),
        "resilience_grade": (
            "A" if supplier.risk_score >= 85 else
            "B" if supplier.risk_score >= 70 else
            "C" if supplier.risk_score >= 50 else
            "D" if supplier.risk_score >= 30 else "F"
        ),
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
    }

    if supplier.on_time_rate >= 95:
        scorecard["strengths"].append("Excellent on-time delivery record")
    if supplier.geopolitical_risk < 30:
        scorecard["strengths"].append("Low geopolitical risk location")
    if supplier.financial_stability == "stable":
        scorecard["strengths"].append("Strong financial stability")
    if len(supplier.alternative_supplier_ids or []) >= 2:
        scorecard["strengths"].append("Multiple alternative suppliers available")

    if supplier.on_time_rate < 85:
        scorecard["weaknesses"].append("Below-average on-time delivery rate")
    if supplier.geopolitical_risk >= 60:
        scorecard["weaknesses"].append("High geopolitical risk in operating region")
    if supplier.financial_stability == "watch":
        scorecard["weaknesses"].append("Financial stability under review")
    if supplier.avg_lead_time_days > 20:
        scorecard["weaknesses"].append("Long average lead time")

    if supplier.risk_score < 60:
        scorecard["recommendations"].append("Consider activating alternative supplier contracts")
    if supplier.geopolitical_risk >= 60:
        scorecard["recommendations"].append("Diversify sourcing to reduce geopolitical concentration")
    if supplier.on_time_rate < 90:
        scorecard["recommendations"].append("Negotiate SLA improvements or increase safety stock")

    return success_response(scorecard)
