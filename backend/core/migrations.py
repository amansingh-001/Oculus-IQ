from __future__ import annotations

from sqlalchemy import text

from core.config import settings
from core.database import engine


SHIPMENT_COLUMNS: dict[str, str] = {
    "tracking_number": "TEXT DEFAULT ''",
    "operator_name": "TEXT DEFAULT ''",
    "vessel_name": "TEXT DEFAULT ''",
    "voyage_number": "TEXT DEFAULT ''",
    "origin_port_id": "TEXT DEFAULT ''",
    "dest_port_id": "TEXT DEFAULT ''",
    "dock_terminal": "TEXT DEFAULT ''",
    "berth": "TEXT DEFAULT ''",
    "etd": "DATETIME DEFAULT NULL",
    "ata": "DATETIME DEFAULT NULL",
    "customs_status": "TEXT DEFAULT 'pending'",
    "priority": "TEXT DEFAULT 'normal'",
}


async def run_sqlite_safe_migrations() -> None:
    """Additive SQLite migrations for prototype DBs.

    SQLite can safely add columns, but existing tables cannot be reshaped in
    place. Every added column here is nullable or has a default and never uses
    NOT NULL, so existing local databases keep working.
    """
    if not settings.database_url.startswith("sqlite"):
        return

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(shipments)"))
        existing = {row[1] for row in result.fetchall()}

        for column, ddl in SHIPMENT_COLUMNS.items():
            if column not in existing:
                await conn.execute(text(f"ALTER TABLE shipments ADD COLUMN {column} {ddl}"))
