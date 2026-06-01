# OculusIQ - Freight Intelligence Platform

AI-powered supply chain intelligence for freight forwarders and mid-market exporters.
See disruptions before they cascade. Act before your clients notice.

## Who This Is For

OculusIQ is built for freight forwarders managing multiple shipper clients and mid-market exporters who ship 500-5,000 containers per year.
If your team spends the day checking carrier portals, forwarding alerts manually, and finding out about disruptions from clients instead of tools, OculusIQ is built for you.

## What Is New In V3

- Operations Command Map: combined map and port network with cargo, ports, routes, and external risk layers.
- Scenario Planner modal: top-right quick simulation for disruption planning.
- Add Client wizard: six-step client and cargo onboarding with DB-backed persistence.
- Intelligence Scan Now: persists scans and displays the latest intelligence summary.
- External risk feed: GDACS events ingested and shown on the map.
- DB-backed create APIs for clients, shipments, ports, and routes.
- CSV import with validation and optional Nominatim geocoding for city coordinates.

## Core Capabilities

- Client Portfolio: monitor all forwarder clients, active cargo, SLA risk, and at-risk shipments.
- Cargo Portfolio: filter shipments by client, lane, carrier, mode, risk, and tariff exposure.
- SLA Breach Predictor: identify clients likely to miss contracted on-time performance.
- Tariff Intelligence: calculate landed cost, tariff exposure, insurance, and handling.
- Carbon Tracker: estimate shipment CO2 and route carbon tradeoffs.
- Risk Scenario Studio: run what-if disruption scenarios and show client impact.
- Intelligence Center: anomaly detection, cascade analysis, and external risk events.
- Operations Command Map: visualize cargo, routes, ports, chokepoints, and disruptions.

## Tech Stack

- Backend: FastAPI, SQLAlchemy async, SQLite WAL, APScheduler, httpx, Pydantic settings.
- AI: Gemini 1.5 Flash via `google-generativeai`, with fallback responses when no key is configured.
- Frontend: React 18, Vite, Tailwind, React Query, React Router, Leaflet, Recharts, Three.js.

## Local Setup

### One-command startup

- Windows: `start.bat`
- macOS/Linux: `./start.sh` (ensure it is executable)

### Backend (manual)

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

### Frontend (manual)

```powershell
Set-Location frontend
npm install
npm run dev
```

## Environment Variables

Create `backend/.env` only if you want live AI or to override defaults.
Use `backend/.env.example` as a template.

```
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite+aiosqlite:///./data/shipments.db
PORT=8000
OPEN_METEO_BASE=https://api.open-meteo.com/v1
NOMINATIM_BASE=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=OculusIQ/0.1 (contact: you@example.com)
```

## API Base

`http://localhost:8000/api/v1`

## Key Endpoints

- `GET /health`
- `GET /health/feeds`
- `POST /clients`
- `POST /shipments`
- `POST /ports`
- `POST /routes`
- `GET /clients/sla-overview`
- `POST /intelligence/scan`
- `GET /intelligence/scans/latest`
- `GET /intelligence/external-risks`
- `POST /documents/import-csv`
- `GET /documents/template`
- `PATCH /shipments/{shipment_id}`
- `POST /simulation/run`

## CSV Import Schema

```
shipment_id, client_name, origin_city, origin_country, dest_city, dest_country,
carrier, mode, status, eta, cargo_type, cargo_value_usd, weight_kg, bl_number,
po_number, incoterm, hs_code, container_number
```

Computed fields (risk score, coordinates, waypoints) are generated after import.

## Important Local Notes

- SQLite has no migrations in this MVP. After model changes, delete:
	- `backend/data/shipments.db`
	- `backend/data/shipments.db-wal`
	- `backend/data/shipments.db-shm`
- `/copilot` and `/settings` redirect to `/`.
- `/ports` redirects to `/map` (Operations Command Map).

## Deployment Notes

- Frontend API base can be set with `VITE_API_BASE`.
- SQLite is for local MVP usage. Use a managed DB for production.

## Verification

```
python -m compileall backend
npm run build
```
