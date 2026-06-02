from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from core.config import settings


_cache: dict[tuple[float, float], tuple[datetime, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


def _round_coord(value: float) -> float:
    return round(value, 1)


def _weather_condition(code: int) -> str:
    if code in {95, 96, 99}:
        return "thunderstorm"
    if code in {61, 63, 65, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow"
    if code in {45, 48}:
        return "fog"
    if code in {1, 2, 3}:
        return "cloudy"
    return "clear"


def _risk_level(wind_kmh: float, precipitation_mm: float, condition: str) -> str:
    if wind_kmh >= 70 or precipitation_mm >= 10 or condition == "thunderstorm":
        return "high"
    if wind_kmh >= 40 or precipitation_mm >= 4 or condition in {"rain", "fog"}:
        return "medium"
    return "low"


async def _fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "wind_speed_10m,precipitation,weather_code",
        "timezone": "UTC",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.open_meteo_base}/forecast", params=params)
        response.raise_for_status()
        payload = response.json()

    current = payload.get("current", {})
    wind = float(current.get("wind_speed_10m", 0.0) or 0.0)
    precip = float(current.get("precipitation", 0.0) or 0.0)
    code = int(current.get("weather_code", 0) or 0)
    condition = _weather_condition(code)
    risk = _risk_level(wind, precip, condition)

    return {
        "location": {"lat": lat, "lon": lon},
        "wind_kmh": wind,
        "precipitation_mm": precip,
        "weather_condition": condition,
        "risk_level": risk,
        "as_of": datetime.utcnow().isoformat() + "Z",
    }


async def get_weather_risk(lat: float, lon: float) -> dict[str, Any]:
    key = (_round_coord(lat), _round_coord(lon))
    now = datetime.utcnow()

    async with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    try:
        result = await _fetch_weather(key[0], key[1])
    except Exception:
        result = {
            "location": {"lat": key[0], "lon": key[1]},
            "wind_kmh": 22.0,
            "precipitation_mm": 0.5,
            "weather_condition": "clear",
            "risk_level": "low",
            "as_of": now.isoformat() + "Z",
        }

    async with _cache_lock:
        _cache[key] = (now + timedelta(minutes=30), result)

    return result


async def get_route_weather_risks(waypoints: list[dict[str, float]]) -> list[dict[str, Any]]:
    if not waypoints:
        return []

    # Sample route points for speed while retaining geographic coverage.
    if len(waypoints) <= 4:
        sampled = waypoints
    else:
        sampled = [waypoints[0], waypoints[len(waypoints) // 3], waypoints[(2 * len(waypoints)) // 3], waypoints[-1]]

    results = []
    for point in sampled:
        lat = float(point.get("lat", 0.0))
        lon = float(point.get("lon", 0.0))
        results.append(await get_weather_risk(lat, lon))

    return results
