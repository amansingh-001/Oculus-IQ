from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Disruption


GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

DISRUPTION_KEYWORDS: dict[str, list[str]] = {
    "weather": ["typhoon", "cyclone", "hurricane", "storm", "flood", "fog"],
    "congestion": ["port strike", "port congestion", "dock workers", "port closure", "backlog"],
    "geopolitical": ["suez", "red sea", "strait", "blockade", "sanctions", "conflict"],
    "operational": ["carrier delay", "vessel fire", "ship grounded", "container shortage"],
}

REGION_KEYWORDS: dict[str, list[str]] = {
    "South China Sea": ["south china sea", "taiwan strait", "hong kong", "shanghai"],
    "Red Sea": ["red sea", "suez", "aden", "houthi", "yemen"],
    "North Sea": ["rotterdam", "hamburg", "antwerp", "felixstowe"],
}

REGION_COORDS: dict[str, dict[str, float]] = {
    "South China Sea": {"lat": 18.0, "lon": 115.0, "radius_km": 900},
    "Red Sea": {"lat": 30.4, "lon": 32.3, "radius_km": 1000},
    "North Sea": {"lat": 52.1, "lon": 4.2, "radius_km": 600},
}

SEVERITY_MAP = {
    "weather": "high",
    "congestion": "medium",
    "geopolitical": "critical",
    "operational": "medium",
}

DELAY_MAP = {
    "weather": 48,
    "congestion": 36,
    "geopolitical": 72,
    "operational": 24,
}


def _parse_seen_date(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _match_article(article: dict[str, Any]) -> dict[str, Any] | None:
    title = (article.get("title") or "").lower()
    if not title:
        return None

    category = next(
        (key for key, keywords in DISRUPTION_KEYWORDS.items() if any(word in title for word in keywords)),
        None,
    )
    region = next(
        (key for key, keywords in REGION_KEYWORDS.items() if any(word in title for word in keywords)),
        None,
    )

    if not category or not region:
        return None

    coords = REGION_COORDS.get(region)
    if not coords:
        return None

    return {
        "type": category,
        "region": region,
        "severity": SEVERITY_MAP.get(category, "medium"),
        "lat": coords["lat"],
        "lon": coords["lon"],
        "radius_km": coords["radius_km"],
        "estimated_delay_hours": DELAY_MAP.get(category, 24),
    }


async def fetch_gdelt_articles(max_records: int = 10) -> list[dict[str, Any]]:
    query = "port disruption shipping supply chain strike typhoon"
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "format": "json",
    }

    headers = {"User-Agent": "OculusIQ/0.1 (local demo)"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(GDELT_BASE, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    return payload.get("articles", []) or []


async def ingest_gdelt_disruptions(db: AsyncSession) -> dict[str, Any]:
    articles = await fetch_gdelt_articles()
    created = 0
    skipped = 0
    disruption_count = int((await db.scalar(select(func.count()).select_from(Disruption))) or 0)

    for article in articles:
        url = (article.get("url") or "").strip()
        if not url:
            skipped += 1
            continue

        existing = await db.scalar(
            select(Disruption.id).where(Disruption.source == "gdelt", Disruption.source_ref == url)
        )
        if existing is not None:
            skipped += 1
            continue

        match = _match_article(article)
        if not match:
            skipped += 1
            continue

        disruption_count += 1
        disruption_id = f"DIS-{disruption_count:04d}"
        detected_at = _parse_seen_date(article.get("seendate"))

        disruption = Disruption(
            id=disruption_id,
            type=match["type"],
            severity=match["severity"],
            title=article.get("title") or "GDELT disruption",
            description=article.get("url") or "GDELT disruption alert",
            region_lat=match["lat"],
            region_lon=match["lon"],
            radius_km=match["radius_km"],
            affected_shipments=[],
            detected_at=detected_at,
            estimated_delay_hours=match["estimated_delay_hours"],
            confidence=0.65,
            active=True,
            source="gdelt",
            source_ref=url,
            reliability=0.7,
            last_updated=detected_at,
        )
        db.add(disruption)
        created += 1
        if created >= 5:
            break

    if created:
        await db.commit()

    return {"created": created, "skipped": skipped}
