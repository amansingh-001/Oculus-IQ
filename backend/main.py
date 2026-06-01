from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from core.responses import success_response
from core.scheduler import start_scheduler, stop_scheduler
from data.seed_clients import seed_clients
from data.seed_shipments import seed_database
from data.seed_ports import seed_ports
from data.seed_suppliers import seed_suppliers
from routers import agent, alerts, carbon, clients, copilot, disruptions, documents, health, intelligence, ports, routes, shipments, simulation, suppliers, tariff
from services.weather_service import get_weather_risk


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    await seed_clients()
    await seed_database()
    await seed_ports()
    await seed_suppliers()
    # Load route graph after seeding ports
    from services.route_optimizer import route_graph
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await route_graph.load_from_db(session)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="OculusIQ API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing routes
app.include_router(shipments.router, prefix="/api/v1/shipments", tags=["shipments"])
app.include_router(disruptions.router, prefix="/api/v1/disruptions", tags=["disruptions"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["copilot"])

# New routes — Iteration 2
app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["simulation"])
app.include_router(intelligence.router, prefix="/api/v1/intelligence", tags=["intelligence"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(ports.router, prefix="/api/v1/ports", tags=["ports"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(tariff.router, prefix="/api/v1/tariff", tags=["tariff"])
app.include_router(carbon.router, prefix="/api/v1/carbon", tags=["carbon"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


@app.get("/api/v1/weather/risks")
async def weather_risks():
    hotspots = [
        {"lat": 18.0, "lon": 115.0, "radius_km": 800, "label": "South China Sea"},
        {"lat": 30.4, "lon": 32.3, "radius_km": 900, "label": "Suez / Red Sea"},
        {"lat": 52.1, "lon": 4.2, "radius_km": 500, "label": "North Sea"},
    ]
    zones = []
    for hotspot in hotspots:
        weather = await get_weather_risk(hotspot["lat"], hotspot["lon"])
        zones.append(
            {
                "label": hotspot["label"],
                "lat": hotspot["lat"],
                "lon": hotspot["lon"],
                "radius_km": hotspot["radius_km"],
                "wind_kmh": weather.get("wind_kmh"),
                "precipitation_mm": weather.get("precipitation_mm"),
                "risk_level": weather.get("risk_level"),
                "weather_condition": weather.get("weather_condition"),
            }
        )

    return success_response(zones, meta={"total": len(zones)})


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "OculusIQ", "version": "2.0.0"}
