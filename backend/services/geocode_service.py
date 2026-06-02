from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from core.config import settings


_cache: dict[tuple[str, str], tuple[datetime, tuple[float, float] | None]] = {}
_cache_ttl = timedelta(hours=24)
_cache_lock = asyncio.Lock()
_last_request_at: datetime | None = None
_request_lock = asyncio.Lock()


async def _rate_limit() -> None:
    global _last_request_at
    async with _request_lock:
        now = datetime.utcnow()
        if _last_request_at is not None:
            elapsed = (now - _last_request_at).total_seconds()
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        _last_request_at = datetime.utcnow()


async def geocode_city(city: str, country: str) -> tuple[float, float] | None:
    if not city:
        return None

    key = (city.lower().strip(), country.lower().strip())
    now = datetime.utcnow()

    async with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    await _rate_limit()

    params: dict[str, Any] = {
        "q": f"{city}, {country}" if country else city,
        "format": "json",
        "limit": 1,
    }

    headers = {
        "User-Agent": settings.nominatim_user_agent or "OculusIQ/0.1 (local demo)",
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(f"{settings.nominatim_base}/search", params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    result = None
    if payload:
        try:
            lat = float(payload[0].get("lat"))
            lon = float(payload[0].get("lon"))
            result = (lat, lon)
        except (TypeError, ValueError):
            result = None

    async with _cache_lock:
        _cache[key] = (now + _cache_ttl, result)

    return result
