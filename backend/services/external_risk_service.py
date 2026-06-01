from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ExternalRiskEvent


GDACS_URL = (
    "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    "?eventtype=TC,FL,EQ,VO&alertlevel=Red,Orange&limit=20"
)

EVENT_TYPE_MAP = {"TC": "weather", "FL": "weather", "DR": "weather", "EQ": "geopolitical", "VO": "geopolitical"}
SEVERITY_MAP = {"Red": "critical", "Orange": "high", "Green": "medium"}


def _parse_dt(value: Any) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


def _coords(feature: dict[str, Any]) -> tuple[float, float] | None:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if isinstance(coordinates, list) and len(coordinates) >= 2:
        try:
            return float(coordinates[1]), float(coordinates[0])
        except (TypeError, ValueError):
            return None
    return None


def _event_id(props: dict[str, Any], title: str, lat: float, lon: float) -> str:
    source_ref = props.get("eventid") or props.get("event_id") or props.get("id")
    if source_ref:
        return f"GDACS-{source_ref}"
    compact = "".join(ch for ch in title.upper() if ch.isalnum())[:32]
    return f"GDACS-{compact}-{round(lat, 2)}-{round(lon, 2)}"


def _event_url(props: dict[str, Any]) -> str | None:
    value = props.get("url") or props.get("link")
    if isinstance(value, dict):
        return value.get("report") or value.get("details") or value.get("geometry")
    if value is None:
        return None
    return str(value)


async def refresh_external_risks(db: AsyncSession) -> list[ExternalRiskEvent]:
    """Fetch GDACS public events and upsert active external risk events."""
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(GDACS_URL)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        result = await db.execute(
            select(ExternalRiskEvent)
            .where(ExternalRiskEvent.active.is_(True))
            .order_by(ExternalRiskEvent.last_updated.desc())
        )
        return result.scalars().all()

    features = payload.get("features") if isinstance(payload, dict) else payload
    if not isinstance(features, list):
        features = []

    seen_ids: set[str] = set()
    now = datetime.utcnow()

    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or feature
        if not isinstance(props, dict):
            continue
        coords = _coords(feature)
        if coords is None:
            continue

        lat, lon = coords
        source_type = str(props.get("eventtype") or props.get("eventType") or props.get("type") or "").upper()
        alert_level = str(props.get("alertlevel") or props.get("alertLevel") or "Orange").title()
        title = str(props.get("eventname") or props.get("name") or props.get("title") or f"GDACS {source_type} event")
        event_id = _event_id(props, title, lat, lon)
        seen_ids.add(event_id)

        event = await db.get(ExternalRiskEvent, event_id)
        if event is None:
            event = ExternalRiskEvent(id=event_id)
            db.add(event)

        event.title = title
        event.event_type = EVENT_TYPE_MAP.get(source_type, "weather")
        event.source_event_type = source_type or "UNKNOWN"
        event.severity = SEVERITY_MAP.get(alert_level, "medium")
        event.alert_level = alert_level
        event.lat = lat
        event.lon = lon
        event.radius_km = 900 if source_type == "TC" else 500
        event.url = _event_url(props)
        event.active = True
        event.source = "gdacs"
        event.source_ref = str(props.get("eventid") or props.get("id") or "")
        event.raw_payload = props
        event.detected_at = _parse_dt(props.get("todate") or props.get("fromdate"))
        event.last_updated = now

    existing_result = await db.execute(select(ExternalRiskEvent).where(ExternalRiskEvent.source == "gdacs"))
    for event in existing_result.scalars().all():
        if event.id not in seen_ids and event.active:
            event.active = False
            event.last_updated = now

    await db.commit()

    result = await db.execute(
        select(ExternalRiskEvent)
        .where(ExternalRiskEvent.active.is_(True))
        .order_by(ExternalRiskEvent.last_updated.desc())
    )
    return result.scalars().all()
