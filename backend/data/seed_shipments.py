from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from data.seed_clients import CLIENTS
from models import Alert, Client, Disruption, Shipment


RISK_FACTOR_TEMPLATES = [
    "Typhoon Kira approaching route (ETA 18h, Cat 3)",
    "Port of Shanghai operating at 94% capacity",
    "Suez Canal experiencing increased wait times (+24h)",
    "Carrier vessel flagged for mechanical inspection",
    "Red Sea tension rerouting via Cape of Good Hope adding 14 days",
    "Dense fog advisory: Strait of Malacca visibility below 500m",
    "French port strike impacting transshipment windows",
    "Bay of Bengal cyclone watch with escalation probability",
    "Rotterdam cold storage utilization nearing hard capacity",
    "Historical delay rate on this lane elevated over 90-day average",
]

ROUTE_TEMPLATES = [
    {
        "origin_city": "Shanghai",
        "origin_country": "China",
        "origin_lat": 31.2,
        "origin_lon": 121.5,
        "dest_city": "Rotterdam",
        "dest_country": "Netherlands",
        "dest_lat": 51.9,
        "dest_lon": 4.5,
        "mode": "sea",
        "duration_days": 28,
    },
    {
        "origin_city": "Mumbai",
        "origin_country": "India",
        "origin_lat": 19.1,
        "origin_lon": 72.9,
        "dest_city": "Hamburg",
        "dest_country": "Germany",
        "dest_lat": 53.5,
        "dest_lon": 10.0,
        "mode": "sea",
        "duration_days": 18,
    },
    {
        "origin_city": "Los Angeles",
        "origin_country": "United States",
        "origin_lat": 34.0,
        "origin_lon": -118.2,
        "dest_city": "Tokyo",
        "dest_country": "Japan",
        "dest_lat": 35.7,
        "dest_lon": 139.7,
        "mode": "sea",
        "duration_days": 12,
    },
    {
        "origin_city": "Dubai",
        "origin_country": "United Arab Emirates",
        "origin_lat": 25.2,
        "origin_lon": 55.3,
        "dest_city": "Frankfurt",
        "dest_country": "Germany",
        "dest_lat": 50.1,
        "dest_lon": 8.7,
        "mode": "air",
        "duration_days": 2,
    },
    {
        "origin_city": "Shenzhen",
        "origin_country": "China",
        "origin_lat": 22.5,
        "origin_lon": 114.1,
        "dest_city": "Los Angeles",
        "dest_country": "United States",
        "dest_lat": 34.0,
        "dest_lon": -118.2,
        "mode": "sea",
        "duration_days": 16,
    },
    {
        "origin_city": "Singapore",
        "origin_country": "Singapore",
        "origin_lat": 1.3,
        "origin_lon": 103.8,
        "dest_city": "London",
        "dest_country": "United Kingdom",
        "dest_lat": 51.5,
        "dest_lon": -0.1,
        "mode": "multimodal",
        "duration_days": 20,
    },
    {
        "origin_city": "Istanbul",
        "origin_country": "Turkey",
        "origin_lat": 41.0,
        "origin_lon": 28.9,
        "dest_city": "New York",
        "dest_country": "United States",
        "dest_lat": 40.7,
        "dest_lon": -74.0,
        "mode": "sea",
        "duration_days": 12,
    },
    {
        "origin_city": "Chennai",
        "origin_country": "India",
        "origin_lat": 13.1,
        "origin_lon": 80.3,
        "dest_city": "Sydney",
        "dest_country": "Australia",
        "dest_lat": -33.9,
        "dest_lon": 151.2,
        "mode": "sea",
        "duration_days": 14,
    },
]

CARRIERS = [
    "Maersk",
    "MSC",
    "COSCO",
    "DHL",
    "FedEx",
    "UPS",
    "Emirates SkyCargo",
    "CMA CGM",
    "Hapag-Lloyd",
    "Evergreen",
]

CARGO_TYPES = [
    "Electronics",
    "Pharmaceuticals",
    "Automotive Parts",
    "Textiles",
    "Chemicals",
    "Food",
]

HS_CODES = {
    "Electronics": ["854231", "851762", "850440", "847130"],
    "Pharmaceuticals": ["300490", "300215", "300420", "300660"],
    "Automotive Parts": ["870899", "840991", "870830", "851220"],
    "Textiles": ["620342", "610910", "520832", "630790"],
    "Chemicals": ["280300", "291590", "320417", "382499"],
    "Food": ["090411", "100630", "200989", "210690"],
}

WEIGHT_RANGES_KG = {
    "Electronics": (5_000, 15_000),
    "Pharmaceuticals": (2_000, 9_000),
    "Automotive Parts": (8_000, 24_000),
    "Textiles": (8_000, 22_000),
    "Chemicals": (10_000, 26_000),
    "Food": (12_000, 28_000),
}

INCOTERMS = ["FOB", "CIF", "EXW", "DDP"]
CITY_PORTS = {
    "Shanghai": "CNSHA",
    "Rotterdam": "NLRTM",
    "Mumbai": "INNSAV",
    "Hamburg": "DEHAM",
    "Los Angeles": "USLA",
    "Tokyo": "JPTYO",
    "Dubai": "AEJEA",
    "Frankfurt": "DEFRA",
    "Shenzhen": "CNSZN",
    "Singapore": "SGSIN",
    "London": "GBFXT",
    "Istanbul": "TRIST",
    "New York": "USNYC",
    "Chennai": "INMAA",
    "Sydney": "AUSYD",
}

DISRUPTION_SCENARIOS = [
    {
        "type": "weather",
        "title": "Typhoon Kira",
        "region": "South China Sea",
        "severity": "high",
        "lat": 18.0,
        "lon": 115.0,
        "radius_km": 1200,
        "estimated_delay_hours": 48,
    },
    {
        "type": "congestion",
        "title": "Rotterdam Port Backlog",
        "region": "North Sea",
        "severity": "medium",
        "lat": 52.1,
        "lon": 4.2,
        "radius_km": 500,
        "estimated_delay_hours": 20,
    },
    {
        "type": "geopolitical",
        "title": "Suez Canal Closure",
        "region": "Red Sea",
        "severity": "critical",
        "lat": 30.4,
        "lon": 32.3,
        "radius_km": 1100,
        "estimated_delay_hours": 72,
    },
]

SEED_DISRUPTIONS = [
    {
        "type": "weather",
        "severity": "high",
        "title": "Typhoon Kira Projected Landfall",
        "description": "High-impact tropical system projected across major lane.",
        "lat": 18.0,
        "lon": 115.0,
        "radius_km": 900,
        "estimated_delay_hours": 48,
    },
    {
        "type": "weather",
        "severity": "medium",
        "title": "North Atlantic Storm Cell",
        "description": "Storm system increasing wave-height risk.",
        "lat": 50.0,
        "lon": -25.0,
        "radius_km": 700,
        "estimated_delay_hours": 26,
    },
    {
        "type": "congestion",
        "severity": "high",
        "title": "Port of Shanghai Berth Saturation",
        "description": "Capacity pressure causing departure slot delays.",
        "lat": 31.2,
        "lon": 121.5,
        "radius_km": 350,
        "estimated_delay_hours": 24,
    },
    {
        "type": "congestion",
        "severity": "medium",
        "title": "Rotterdam Yard Overflow",
        "description": "Container backlog extends handling cycle times.",
        "lat": 51.9,
        "lon": 4.5,
        "radius_km": 350,
        "estimated_delay_hours": 16,
    },
    {
        "type": "geopolitical",
        "severity": "critical",
        "title": "Suez Security Escalation",
        "description": "Transit advisories forcing reroute options.",
        "lat": 30.4,
        "lon": 32.3,
        "radius_km": 1000,
        "estimated_delay_hours": 60,
    },
    {
        "type": "operational",
        "severity": "medium",
        "title": "Bridge Closure on Inland Corridor",
        "description": "Road/rail intermodal throughput constraints observed.",
        "lat": 48.9,
        "lon": 2.4,
        "radius_km": 250,
        "estimated_delay_hours": 12,
    },
    {
        "type": "operational",
        "severity": "high",
        "title": "Carrier Mechanical Inspection Hold",
        "description": "Fleet inspection checkpoints affecting dispatch.",
        "lat": 24.0,
        "lon": 56.0,
        "radius_km": 500,
        "estimated_delay_hours": 30,
    },
    {
        "type": "operational",
        "severity": "medium",
        "title": "Warehouse Automation Outage",
        "description": "Fulfillment synchronization degraded for outbound loading.",
        "lat": 52.5,
        "lon": 13.4,
        "radius_km": 220,
        "estimated_delay_hours": 10,
    },
]

_scenario_index = 0


def next_disruption_scenario() -> dict:
    global _scenario_index
    scenario = DISRUPTION_SCENARIOS[_scenario_index % len(DISRUPTION_SCENARIOS)]
    _scenario_index += 1
    return dict(scenario)


def _risk_level_from_score(score: int) -> str:
    if score <= 25:
        return "low"
    if score <= 50:
        return "medium"
    if score <= 75:
        return "high"
    return "critical"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _interpolate_lat_lon(route: dict, progress: float) -> tuple[float, float]:
    lat = route["origin_lat"] + (route["dest_lat"] - route["origin_lat"]) * progress
    lon = route["origin_lon"] + (route["dest_lon"] - route["origin_lon"]) * progress
    return lat, lon


def _build_waypoints(route: dict) -> list[dict]:
    mid_lat = (route["origin_lat"] + route["dest_lat"]) / 2
    mid_lon = (route["origin_lon"] + route["dest_lon"]) / 2
    return [
        {"lat": route["origin_lat"], "lon": route["origin_lon"]},
        {"lat": mid_lat, "lon": mid_lon},
        {"lat": route["dest_lat"], "lon": route["dest_lon"]},
    ]


def _pick_risk_score(rng: random.Random) -> int:
    bucket = rng.choices(["low", "medium", "high", "critical"], weights=[40, 30, 20, 10], k=1)[0]
    if bucket == "low":
        return rng.randint(5, 25)
    if bucket == "medium":
        return rng.randint(26, 50)
    if bucket == "high":
        return rng.randint(51, 75)
    return rng.randint(76, 97)


def _tariff_rate(origin: str, dest: str, hs_code: str) -> float:
    dest_region = "EU" if dest in {"Germany", "Netherlands", "Belgium", "France"} else dest
    key = (origin, dest_region, hs_code[:1])
    matrix = {
        ("China", "United States", "8"): 145.0,
        ("China", "United States", "6"): 25.0,
        ("India", "United States", "6"): 0.0,
        ("India", "EU", "3"): 0.0,
        ("India", "United Arab Emirates", "8"): 0.0,
        ("United Arab Emirates", "EU", "8"): 3.0,
        ("Singapore", "United Kingdom", "8"): 2.0,
        ("Turkey", "United States", "6"): 8.0,
    }
    return matrix.get(key, 5.0)


def _route_distance(route: dict, mode: str) -> float:
    direct = _haversine_km(route["origin_lat"], route["origin_lon"], route["dest_lat"], route["dest_lon"])
    factor = 1.18 if mode == "air" else 1.35 if mode == "sea" else 1.45
    return round(direct * factor, 1)


def _build_shipments(count: int = 500) -> list[Shipment]:
    rng = random.Random(42)
    now = datetime.utcnow()
    rows: list[Shipment] = []
    client_weights = [client["annual_shipment_count"] for client in CLIENTS]

    for idx in range(1, count + 1):
        route = ROUTE_TEMPLATES[(idx - 1) % len(ROUTE_TEMPLATES)]
        client = rng.choices(CLIENTS, weights=client_weights, k=1)[0]
        cargo_type = rng.choice(CARGO_TYPES)
        hs_code = rng.choice(HS_CODES[cargo_type])
        route_distance_km = _route_distance(route, route["mode"])
        weight_min, weight_max = WEIGHT_RANGES_KG[cargo_type]
        weight_kg = rng.randint(weight_min, weight_max)
        tariff_rate_pct = _tariff_rate(route["origin_country"], route["dest_country"], hs_code)
        cargo_value = rng.randint(45_000, 1_800_000)
        tariff_adjusted_cost = cargo_value + (cargo_value * tariff_rate_pct / 100)
        score = _pick_risk_score(rng)
        level = _risk_level_from_score(score)
        status = rng.choices(
            ["in_transit", "pending", "delayed", "delivered"],
            weights=[65, 15, 15, 5],
            k=1,
        )[0]

        if status == "in_transit":
            progress = rng.uniform(0.08, 0.92)
        elif status == "pending":
            progress = rng.uniform(0.0, 0.08)
        elif status == "delayed":
            progress = rng.uniform(0.15, 0.7)
        else:
            progress = 1.0

        curr_lat, curr_lon = _interpolate_lat_lon(route, progress)
        curr_lat += rng.uniform(-0.6, 0.6)
        curr_lon += rng.uniform(-0.6, 0.6)

        shipment = Shipment(
            id=f"SHP-{idx:06d}",
            client_id=client["id"],
            client_name=client["name"],
            origin_city=route["origin_city"],
            origin_country=route["origin_country"],
            origin_lat=route["origin_lat"],
            origin_lon=route["origin_lon"],
            dest_city=route["dest_city"],
            dest_country=route["dest_country"],
            dest_lat=route["dest_lat"],
            dest_lon=route["dest_lon"],
            carrier=rng.choice(CARRIERS),
            mode=route["mode"],
            status=status,
            eta=now + timedelta(days=route["duration_days"] + rng.randint(-2, 4)),
            risk_score=score,
            risk_level=level,
            risk_factors=rng.sample(RISK_FACTOR_TEMPLATES, k=rng.randint(1, 3)),
            current_lat=curr_lat,
            current_lon=curr_lon,
            route_waypoints=_build_waypoints(route),
            cargo_value_usd=cargo_value,
            cargo_type=cargo_type,
            container_number=f"CONT{rng.randint(100000, 999999)}",
            tracking_number=f"TRK{idx:06d}{rng.randint(100, 999)}",
            operator_name=rng.choice(CARRIERS),
            vessel_name=f"Oculus Trader {rng.randint(1, 24)}",
            voyage_number=f"VY{rng.randint(1000, 9999)}",
            origin_port_id=CITY_PORTS.get(route["origin_city"], ""),
            dest_port_id=CITY_PORTS.get(route["dest_city"], ""),
            dock_terminal=f"T{rng.randint(1, 6)}",
            berth=f"B{rng.randint(1, 18)}",
            etd=now - timedelta(days=rng.randint(0, 5)),
            ata=now + timedelta(days=route["duration_days"] + rng.randint(-1, 5)) if status == "delivered" else None,
            customs_status=rng.choices(["pending", "cleared", "inspection", "hold"], weights=[45, 40, 12, 3], k=1)[0],
            priority=rng.choices(["normal", "high", "urgent"], weights=[72, 22, 6], k=1)[0],
            incoterm=rng.choice(INCOTERMS),
            hs_code=hs_code,
            tariff_rate_pct=tariff_rate_pct,
            tariff_adjusted_cost_usd=round(tariff_adjusted_cost),
            po_number=f"PO-2026-{rng.randint(1000, 9999)}",
            bl_number=f"MAEU{rng.randint(100_000_000, 999_999_999)}",
            lc_expiry_date=now + timedelta(days=route["duration_days"] + rng.randint(4, 35)),
            expected_transit_days=route["duration_days"],
            actual_transit_days=route["duration_days"] + rng.randint(1, 8) if status in {"delayed", "delivered"} else None,
            weight_kg=weight_kg,
            route_distance_km=route_distance_km,
            notes=None,
            source="seed",
            reliability=0.65,
            last_updated=now - timedelta(minutes=rng.randint(0, 45)),
        )
        rows.append(shipment)

    return rows


def _affected_shipments(shipments: list[Shipment], lat: float, lon: float, radius_km: int) -> list[str]:
    affected = []
    for shipment in shipments:
        distance = _haversine_km(shipment.current_lat, shipment.current_lon, lat, lon)
        if distance <= radius_km:
            affected.append(shipment.id)
    return affected


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(Shipment))
        if existing and existing > 0:
            return

        shipments = _build_shipments(500)
        session.add_all(shipments)
        await session.flush()

        disruptions: list[Disruption] = []
        for idx, template in enumerate(SEED_DISRUPTIONS, start=1):
            affected = _affected_shipments(shipments, template["lat"], template["lon"], template["radius_km"])
            disruptions.append(
                Disruption(
                    id=f"DIS-{idx:04d}",
                    type=template["type"],
                    severity=template["severity"],
                    title=template["title"],
                    description=template["description"],
                    region_lat=template["lat"],
                    region_lon=template["lon"],
                    radius_km=template["radius_km"],
                    affected_shipments=affected,
                    detected_at=datetime.utcnow() - timedelta(hours=idx),
                    estimated_delay_hours=template["estimated_delay_hours"],
                    confidence=0.8,
                    active=True,
                    source="seed",
                    source_ref=None,
                    reliability=0.7,
                    last_updated=datetime.utcnow() - timedelta(hours=idx),
                )
            )

        session.add_all(disruptions)

        high_risk = [s for s in shipments if s.risk_level in {"high", "critical"}]
        alerts: list[Alert] = []
        for idx, shipment in enumerate(high_risk[:15], start=1):
            disruption = disruptions[idx % len(disruptions)]
            alerts.append(
                Alert(
                    id=f"ALT-{idx:04d}",
                    shipment_id=shipment.id,
                    disruption_id=disruption.id,
                    priority="urgent" if shipment.risk_score >= 90 else "high",
                    title=f"{shipment.risk_level.title()} Risk: {shipment.id} impacted",
                    ai_summary=f"{shipment.origin_city} to {shipment.dest_city} lane affected by {disruption.title}.",
                    drafted_notification=None,
                    recommended_actions=[
                        "Review AI route alternatives",
                        "Notify customer success desk",
                    ],
                    created_at=datetime.utcnow() - timedelta(minutes=idx * 3),
                    acknowledged=False,
                    source="seed",
                    reliability=0.7,
                    last_updated=datetime.utcnow() - timedelta(minutes=idx * 3),
                )
            )

        session.add_all(alerts)

        client_counts = {}
        for shipment in shipments:
            if shipment.client_id is None:
                continue
            counts = client_counts.setdefault(shipment.client_id, {"active": 0, "at_risk": 0})
            if shipment.status in {"in_transit", "pending", "delayed"}:
                counts["active"] += 1
            if shipment.risk_score >= 60:
                counts["at_risk"] += 1

        for client_id, counts in client_counts.items():
            client = await session.get(Client, client_id)
            if client is not None:
                client.active_shipments_count = counts["active"]
                client.at_risk_shipments_count = counts["at_risk"]

        await session.commit()
