"""Seed data for the global port network and route edges."""
from __future__ import annotations

from sqlalchemy import func, select

from core.database import AsyncSessionLocal
from models import PortNode, RouteEdge


PORTS = [
    # SEA PORTS
    {"id": "CNSHA", "name": "Port of Shanghai", "city": "Shanghai", "country": "China",
     "lat": 31.23, "lon": 121.47, "type": "sea_port", "capacity_teu": 47000000},
    {"id": "SGSIN", "name": "Port of Singapore", "city": "Singapore", "country": "Singapore",
     "lat": 1.26, "lon": 103.82, "type": "sea_port", "capacity_teu": 37000000},
    {"id": "NLRTM", "name": "Port of Rotterdam", "city": "Rotterdam", "country": "Netherlands",
     "lat": 51.90, "lon": 4.47, "type": "sea_port", "capacity_teu": 15000000},
    {"id": "DEHAM", "name": "Port of Hamburg", "city": "Hamburg", "country": "Germany",
     "lat": 53.54, "lon": 9.96, "type": "sea_port", "capacity_teu": 9000000},
    {"id": "USLA", "name": "Port of Los Angeles", "city": "Los Angeles", "country": "USA",
     "lat": 33.73, "lon": -118.26, "type": "sea_port", "capacity_teu": 10000000},
    {"id": "AEJEA", "name": "Port of Jebel Ali", "city": "Dubai", "country": "UAE",
     "lat": 24.99, "lon": 55.05, "type": "sea_port", "capacity_teu": 14500000},
    {"id": "INMAA", "name": "Port of Chennai", "city": "Chennai", "country": "India",
     "lat": 13.08, "lon": 80.29, "type": "sea_port", "capacity_teu": 2000000},
    {"id": "INNSAV", "name": "Nhava Sheva", "city": "Mumbai", "country": "India",
     "lat": 18.95, "lon": 72.95, "type": "sea_port", "capacity_teu": 7000000},
    {"id": "TRIST", "name": "Ambarli Port", "city": "Istanbul", "country": "Turkey",
     "lat": 40.97, "lon": 28.68, "type": "sea_port", "capacity_teu": 3000000},
    {"id": "GBFXT", "name": "Port of Felixstowe", "city": "Felixstowe", "country": "UK",
     "lat": 51.95, "lon": 1.35, "type": "sea_port", "capacity_teu": 4000000},
    {"id": "AUSYD", "name": "Port Botany", "city": "Sydney", "country": "Australia",
     "lat": -33.95, "lon": 151.21, "type": "sea_port", "capacity_teu": 3000000},
    {"id": "JPTYO", "name": "Port of Tokyo", "city": "Tokyo", "country": "Japan",
     "lat": 35.63, "lon": 139.79, "type": "sea_port", "capacity_teu": 5000000},
    {"id": "KRPUS", "name": "Port of Busan", "city": "Busan", "country": "South Korea",
     "lat": 35.10, "lon": 129.04, "type": "sea_port", "capacity_teu": 22000000},
    {"id": "CNSZN", "name": "Port of Shenzhen", "city": "Shenzhen", "country": "China",
     "lat": 22.54, "lon": 114.05, "type": "sea_port", "capacity_teu": 28000000},
    {"id": "USNYC", "name": "Port of New York", "city": "New York", "country": "USA",
     "lat": 40.68, "lon": -74.04, "type": "sea_port", "capacity_teu": 9000000},
    {"id": "BEANR", "name": "Port of Antwerp", "city": "Antwerp", "country": "Belgium",
     "lat": 51.23, "lon": 4.40, "type": "sea_port", "capacity_teu": 14000000},
    {"id": "MYPKG", "name": "Port Klang", "city": "Port Klang", "country": "Malaysia",
     "lat": 3.00, "lon": 101.40, "type": "sea_port", "capacity_teu": 14000000},
    # CHOKEPOINTS
    {"id": "SUEZ_CANAL", "name": "Suez Canal", "city": "Ismailia", "country": "Egypt",
     "lat": 30.58, "lon": 32.26, "type": "chokepoint", "capacity_teu": 999999},
    {"id": "STRAIT_MALACCA", "name": "Strait of Malacca", "city": "Malacca", "country": "Malaysia",
     "lat": 2.50, "lon": 102.0, "type": "chokepoint", "capacity_teu": 999999},
    {"id": "STRAIT_HORMUZ", "name": "Strait of Hormuz", "city": "Hormuz", "country": "Iran",
     "lat": 26.60, "lon": 56.26, "type": "chokepoint", "capacity_teu": 999999},
    {"id": "PANAMA_CANAL", "name": "Panama Canal", "city": "Panama City", "country": "Panama",
     "lat": 9.08, "lon": -79.68, "type": "chokepoint", "capacity_teu": 999999},
    {"id": "CAPE_GOOD_HOPE", "name": "Cape of Good Hope", "city": "Cape Town", "country": "South Africa",
     "lat": -34.36, "lon": 18.47, "type": "chokepoint", "capacity_teu": 999999},
    # AIR HUBS
    {"id": "HKGHK", "name": "Hong Kong Int'l Airport", "city": "Hong Kong", "country": "China",
     "lat": 22.31, "lon": 113.91, "type": "air_hub", "capacity_teu": 5000000},
    {"id": "AEDXB", "name": "Dubai Int'l Airport", "city": "Dubai", "country": "UAE",
     "lat": 25.25, "lon": 55.36, "type": "air_hub", "capacity_teu": 3000000},
    {"id": "USJFK", "name": "JFK Airport", "city": "New York", "country": "USA",
     "lat": 40.64, "lon": -73.78, "type": "air_hub", "capacity_teu": 2000000},
    {"id": "DEFRA", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany",
     "lat": 50.03, "lon": 8.57, "type": "air_hub", "capacity_teu": 2500000},
    {"id": "SGCHN", "name": "Changi Airport", "city": "Singapore", "country": "Singapore",
     "lat": 1.36, "lon": 103.99, "type": "air_hub", "capacity_teu": 2000000},
]

ROUTE_EDGES = [
    # Asia Internal Sea Routes
    {"from": "CNSHA", "to": "SGSIN", "mode": "sea", "dist": 3800, "hours": 120, "cost": 1200, "reliability": 88},
    {"from": "SGSIN", "to": "CNSHA", "mode": "sea", "dist": 3800, "hours": 120, "cost": 1200, "reliability": 88},
    {"from": "CNSHA", "to": "KRPUS", "mode": "sea", "dist": 900, "hours": 36, "cost": 450, "reliability": 92},
    {"from": "KRPUS", "to": "CNSHA", "mode": "sea", "dist": 900, "hours": 36, "cost": 450, "reliability": 92},
    {"from": "CNSHA", "to": "JPTYO", "mode": "sea", "dist": 1800, "hours": 60, "cost": 680, "reliability": 90},
    {"from": "JPTYO", "to": "CNSHA", "mode": "sea", "dist": 1800, "hours": 60, "cost": 680, "reliability": 90},
    {"from": "CNSZN", "to": "SGSIN", "mode": "sea", "dist": 2600, "hours": 84, "cost": 980, "reliability": 87},
    {"from": "SGSIN", "to": "CNSZN", "mode": "sea", "dist": 2600, "hours": 84, "cost": 980, "reliability": 87},
    {"from": "CNSZN", "to": "CNSHA", "mode": "sea", "dist": 1200, "hours": 40, "cost": 500, "reliability": 93},
    {"from": "MYPKG", "to": "SGSIN", "mode": "sea", "dist": 300, "hours": 12, "cost": 200, "reliability": 95},
    {"from": "SGSIN", "to": "MYPKG", "mode": "sea", "dist": 300, "hours": 12, "cost": 200, "reliability": 95},

    # Asia → Malacca → India
    {"from": "SGSIN", "to": "STRAIT_MALACCA", "mode": "sea", "dist": 600, "hours": 18, "cost": 300, "reliability": 90},
    {"from": "STRAIT_MALACCA", "to": "SGSIN", "mode": "sea", "dist": 600, "hours": 18, "cost": 300, "reliability": 90},
    {"from": "STRAIT_MALACCA", "to": "INMAA", "mode": "sea", "dist": 2400, "hours": 78, "cost": 850, "reliability": 84},
    {"from": "INMAA", "to": "STRAIT_MALACCA", "mode": "sea", "dist": 2400, "hours": 78, "cost": 850, "reliability": 84},
    {"from": "STRAIT_MALACCA", "to": "INNSAV", "mode": "sea", "dist": 3500, "hours": 108, "cost": 1100, "reliability": 82},
    {"from": "INNSAV", "to": "STRAIT_MALACCA", "mode": "sea", "dist": 3500, "hours": 108, "cost": 1100, "reliability": 82},

    # India → Middle East → Suez
    {"from": "INNSAV", "to": "AEJEA", "mode": "sea", "dist": 1800, "hours": 60, "cost": 720, "reliability": 86},
    {"from": "AEJEA", "to": "INNSAV", "mode": "sea", "dist": 1800, "hours": 60, "cost": 720, "reliability": 86},
    {"from": "INMAA", "to": "AEJEA", "mode": "sea", "dist": 2700, "hours": 90, "cost": 950, "reliability": 84},
    {"from": "AEJEA", "to": "STRAIT_HORMUZ", "mode": "sea", "dist": 400, "hours": 14, "cost": 250, "reliability": 88},
    {"from": "STRAIT_HORMUZ", "to": "AEJEA", "mode": "sea", "dist": 400, "hours": 14, "cost": 250, "reliability": 88},
    {"from": "AEJEA", "to": "SUEZ_CANAL", "mode": "sea", "dist": 2200, "hours": 72, "cost": 1000, "reliability": 80},
    {"from": "SUEZ_CANAL", "to": "AEJEA", "mode": "sea", "dist": 2200, "hours": 72, "cost": 1000, "reliability": 80},

    # Suez → Europe
    {"from": "SUEZ_CANAL", "to": "NLRTM", "mode": "sea", "dist": 5500, "hours": 168, "cost": 1800, "reliability": 82},
    {"from": "NLRTM", "to": "SUEZ_CANAL", "mode": "sea", "dist": 5500, "hours": 168, "cost": 1800, "reliability": 82},
    {"from": "SUEZ_CANAL", "to": "TRIST", "mode": "sea", "dist": 1200, "hours": 40, "cost": 550, "reliability": 85},
    {"from": "TRIST", "to": "SUEZ_CANAL", "mode": "sea", "dist": 1200, "hours": 40, "cost": 550, "reliability": 85},
    {"from": "NLRTM", "to": "DEHAM", "mode": "sea", "dist": 450, "hours": 16, "cost": 280, "reliability": 94},
    {"from": "DEHAM", "to": "NLRTM", "mode": "sea", "dist": 450, "hours": 16, "cost": 280, "reliability": 94},
    {"from": "NLRTM", "to": "GBFXT", "mode": "sea", "dist": 350, "hours": 14, "cost": 250, "reliability": 93},
    {"from": "GBFXT", "to": "NLRTM", "mode": "sea", "dist": 350, "hours": 14, "cost": 250, "reliability": 93},
    {"from": "NLRTM", "to": "BEANR", "mode": "sea", "dist": 100, "hours": 6, "cost": 120, "reliability": 96},
    {"from": "BEANR", "to": "NLRTM", "mode": "sea", "dist": 100, "hours": 6, "cost": 120, "reliability": 96},

    # Europe → Americas
    {"from": "NLRTM", "to": "USNYC", "mode": "sea", "dist": 5800, "hours": 200, "cost": 2200, "reliability": 85},
    {"from": "USNYC", "to": "NLRTM", "mode": "sea", "dist": 5800, "hours": 200, "cost": 2200, "reliability": 85},
    {"from": "TRIST", "to": "USNYC", "mode": "sea", "dist": 8600, "hours": 288, "cost": 2800, "reliability": 80},

    # Trans-Pacific
    {"from": "CNSHA", "to": "USLA", "mode": "sea", "dist": 10500, "hours": 336, "cost": 3200, "reliability": 82},
    {"from": "USLA", "to": "CNSHA", "mode": "sea", "dist": 10500, "hours": 336, "cost": 3200, "reliability": 82},
    {"from": "CNSZN", "to": "USLA", "mode": "sea", "dist": 11000, "hours": 360, "cost": 3400, "reliability": 80},
    {"from": "JPTYO", "to": "USLA", "mode": "sea", "dist": 8800, "hours": 280, "cost": 2600, "reliability": 84},
    {"from": "USLA", "to": "JPTYO", "mode": "sea", "dist": 8800, "hours": 280, "cost": 2600, "reliability": 84},
    {"from": "KRPUS", "to": "USLA", "mode": "sea", "dist": 9500, "hours": 300, "cost": 2800, "reliability": 83},

    # Panama Canal Route
    {"from": "USLA", "to": "PANAMA_CANAL", "mode": "sea", "dist": 4800, "hours": 156, "cost": 1600, "reliability": 83},
    {"from": "PANAMA_CANAL", "to": "USLA", "mode": "sea", "dist": 4800, "hours": 156, "cost": 1600, "reliability": 83},
    {"from": "PANAMA_CANAL", "to": "USNYC", "mode": "sea", "dist": 3200, "hours": 108, "cost": 1200, "reliability": 85},
    {"from": "USNYC", "to": "PANAMA_CANAL", "mode": "sea", "dist": 3200, "hours": 108, "cost": 1200, "reliability": 85},

    # Cape of Good Hope (alternative to Suez)
    {"from": "INNSAV", "to": "CAPE_GOOD_HOPE", "mode": "sea", "dist": 7200, "hours": 264, "cost": 2800, "reliability": 78},
    {"from": "CAPE_GOOD_HOPE", "to": "INNSAV", "mode": "sea", "dist": 7200, "hours": 264, "cost": 2800, "reliability": 78},
    {"from": "CAPE_GOOD_HOPE", "to": "NLRTM", "mode": "sea", "dist": 10500, "hours": 360, "cost": 3400, "reliability": 76},
    {"from": "NLRTM", "to": "CAPE_GOOD_HOPE", "mode": "sea", "dist": 10500, "hours": 360, "cost": 3400, "reliability": 76},
    {"from": "SGSIN", "to": "CAPE_GOOD_HOPE", "mode": "sea", "dist": 9200, "hours": 312, "cost": 3100, "reliability": 77},

    # Australia
    {"from": "SGSIN", "to": "AUSYD", "mode": "sea", "dist": 6300, "hours": 204, "cost": 2000, "reliability": 86},
    {"from": "AUSYD", "to": "SGSIN", "mode": "sea", "dist": 6300, "hours": 204, "cost": 2000, "reliability": 86},
    {"from": "INMAA", "to": "AUSYD", "mode": "sea", "dist": 8200, "hours": 264, "cost": 2600, "reliability": 83},

    # AIR ROUTES (fast, expensive)
    {"from": "HKGHK", "to": "DEFRA", "mode": "air", "dist": 9200, "hours": 12, "cost": 18000, "reliability": 95},
    {"from": "DEFRA", "to": "HKGHK", "mode": "air", "dist": 9200, "hours": 12, "cost": 18000, "reliability": 95},
    {"from": "HKGHK", "to": "USJFK", "mode": "air", "dist": 12900, "hours": 16, "cost": 22000, "reliability": 93},
    {"from": "USJFK", "to": "HKGHK", "mode": "air", "dist": 12900, "hours": 16, "cost": 22000, "reliability": 93},
    {"from": "AEDXB", "to": "DEFRA", "mode": "air", "dist": 4800, "hours": 6, "cost": 12000, "reliability": 96},
    {"from": "DEFRA", "to": "AEDXB", "mode": "air", "dist": 4800, "hours": 6, "cost": 12000, "reliability": 96},
    {"from": "AEDXB", "to": "USJFK", "mode": "air", "dist": 11000, "hours": 14, "cost": 20000, "reliability": 94},
    {"from": "SGCHN", "to": "DEFRA", "mode": "air", "dist": 10400, "hours": 13, "cost": 19000, "reliability": 94},
    {"from": "DEFRA", "to": "SGCHN", "mode": "air", "dist": 10400, "hours": 13, "cost": 19000, "reliability": 94},
    {"from": "SGCHN", "to": "USJFK", "mode": "air", "dist": 15300, "hours": 19, "cost": 24000, "reliability": 92},
    {"from": "DEFRA", "to": "USJFK", "mode": "air", "dist": 6200, "hours": 8, "cost": 14000, "reliability": 96},
    {"from": "USJFK", "to": "DEFRA", "mode": "air", "dist": 6200, "hours": 8, "cost": 14000, "reliability": 96},
    {"from": "HKGHK", "to": "SGCHN", "mode": "air", "dist": 2600, "hours": 4, "cost": 6000, "reliability": 97},
    {"from": "SGCHN", "to": "HKGHK", "mode": "air", "dist": 2600, "hours": 4, "cost": 6000, "reliability": 97},
    {"from": "HKGHK", "to": "AEDXB", "mode": "air", "dist": 5900, "hours": 8, "cost": 13000, "reliability": 95},
    {"from": "AEDXB", "to": "HKGHK", "mode": "air", "dist": 5900, "hours": 8, "cost": 13000, "reliability": 95},
]


async def seed_ports() -> None:
    """Seed port nodes and route edges if they don't exist yet."""
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(PortNode))
        if existing and existing > 0:
            return

        for p in PORTS:
            session.add(PortNode(
                id=p["id"],
                name=p["name"],
                city=p.get("city"),
                country=p.get("country"),
                lat=p["lat"],
                lon=p["lon"],
                type=p["type"],
                capacity_teu=p.get("capacity_teu"),
                congestion_score=0.0,
                avg_wait_hours=0.0,
                is_active=True,
                source="seed",
                reliability=0.75,
            ))

        await session.flush()

        for e in ROUTE_EDGES:
            session.add(RouteEdge(
                from_port_id=e["from"],
                to_port_id=e["to"],
                mode=e["mode"],
                distance_km=float(e["dist"]),
                base_transit_hours=float(e["hours"]),
                base_cost_usd_per_teu=float(e["cost"]),
                current_delay_factor=1.0,
                reliability_score=float(e["reliability"]),
                is_active=True,
            ))

        await session.commit()
