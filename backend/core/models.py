from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    industry: Mapped[str] = mapped_column(String(80), index=True)
    country: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(120))
    primary_contact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    annual_shipment_count: Mapped[int] = mapped_column(Integer, default=0)
    total_cargo_value_annual_usd: Mapped[float] = mapped_column(Float, default=0.0)
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="medium")
    sla_on_time_pct: Mapped[float] = mapped_column(Float, default=95.0)
    current_sla_performance: Mapped[float] = mapped_column(Float, default=95.0)
    active_shipments_count: Mapped[int] = mapped_column(Integer, default=0)
    at_risk_shipments_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("clients.id"), nullable=True, index=True)
    client_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)

    origin_city: Mapped[str] = mapped_column(String(120))
    origin_country: Mapped[str] = mapped_column(String(120))
    origin_lat: Mapped[float] = mapped_column(Float)
    origin_lon: Mapped[float] = mapped_column(Float)

    dest_city: Mapped[str] = mapped_column(String(120))
    dest_country: Mapped[str] = mapped_column(String(120))
    dest_lat: Mapped[float] = mapped_column(Float)
    dest_lon: Mapped[float] = mapped_column(Float)

    carrier: Mapped[str] = mapped_column(String(80), index=True)
    mode: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)

    eta: Mapped[datetime] = mapped_column(DateTime)
    risk_score: Mapped[int] = mapped_column(Integer, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), index=True)
    risk_factors: Mapped[list[str]] = mapped_column(JSON, default=list)

    current_lat: Mapped[float] = mapped_column(Float)
    current_lon: Mapped[float] = mapped_column(Float)
    route_waypoints: Mapped[list[dict]] = mapped_column(JSON, default=list)

    cargo_value_usd: Mapped[int] = mapped_column(Integer)
    cargo_type: Mapped[str] = mapped_column(String(80))
    container_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(80), nullable=True, default="")
    operator_name: Mapped[str | None] = mapped_column(String(120), nullable=True, default="")
    vessel_name: Mapped[str | None] = mapped_column(String(120), nullable=True, default="")
    voyage_number: Mapped[str | None] = mapped_column(String(60), nullable=True, default="")
    origin_port_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True, default="")
    dest_port_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True, default="")
    dock_terminal: Mapped[str | None] = mapped_column(String(120), nullable=True, default="")
    berth: Mapped[str | None] = mapped_column(String(60), nullable=True, default="")
    etd: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ata: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customs_status: Mapped[str] = mapped_column(String(40), default="pending")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    incoterm: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hs_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tariff_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    tariff_adjusted_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bl_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lc_expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_transit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_transit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="system")
    reliability: Mapped[float] = mapped_column(Float, default=0.7)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Disruption(Base):
    __tablename__ = "disruptions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)

    region_lat: Mapped[float] = mapped_column(Float)
    region_lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[int] = mapped_column(Integer)

    affected_shipments: Mapped[list[str]] = mapped_column(JSON, default=list)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    estimated_delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.75)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="system")
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reliability: Mapped[float] = mapped_column(Float, default=0.7)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(String(20), ForeignKey("shipments.id"), index=True)
    disruption_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("disruptions.id"), nullable=True)

    priority: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(240))
    ai_summary: Mapped[str] = mapped_column(Text)
    drafted_notification: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="system")
    reliability: Mapped[float] = mapped_column(Float, default=0.7)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PortNode(Base):
    __tablename__ = "port_nodes"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(40))
    capacity_teu: Mapped[int | None] = mapped_column(Integer)
    congestion_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_wait_hours: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(40), default="system")
    reliability: Mapped[float] = mapped_column(Float, default=0.7)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RouteEdge(Base):
    __tablename__ = "route_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_port_id: Mapped[str] = mapped_column(String(20), ForeignKey("port_nodes.id"))
    to_port_id: Mapped[str] = mapped_column(String(20), ForeignKey("port_nodes.id"))
    mode: Mapped[str] = mapped_column(String(40))
    distance_km: Mapped[float] = mapped_column(Float)
    base_transit_hours: Mapped[float] = mapped_column(Float)
    base_cost_usd_per_teu: Mapped[float] = mapped_column(Float)
    current_delay_factor: Mapped[float] = mapped_column(Float, default=1.0)
    reliability_score: Mapped[float] = mapped_column(Float, default=85.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_id: Mapped[str] = mapped_column(String(20), ForeignKey("shipments.id"))
    event_type: Mapped[str] = mapped_column(String(40))
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_score_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(40), default="system")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    lat_rounded: Mapped[float] = mapped_column(Float)
    lon_rounded: Mapped[float] = mapped_column(Float)
    wind_kmh: Mapped[float] = mapped_column(Float)
    precipitation_mm: Mapped[float] = mapped_column(Float)
    visibility_km: Mapped[float] = mapped_column(Float)
    wave_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    condition: Mapped[str] = mapped_column(String(40))
    risk_level: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class ExternalRiskEvent(Base):
    __tablename__ = "external_risk_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    source_event_type: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    alert_level: Mapped[str] = mapped_column(String(20))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[int] = mapped_column(Integer, default=600)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="gdacs")
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IntelligenceScan(Base):
    __tablename__ = "intelligence_scans"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="complete")
    scan_type: Mapped[str] = mapped_column(String(40), default="manual")
    anomalies_count: Mapped[int] = mapped_column(Integer, default=0)
    sla_clients_at_risk: Mapped[int] = mapped_column(Integer, default=0)
    cascade_nodes: Mapped[int] = mapped_column(Integer, default=0)
    external_risks_count: Mapped[int] = mapped_column(Integer, default=0)
    weather_risks_count: Mapped[int] = mapped_column(Integer, default=0)
    top_risks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scenario_name: Mapped[str] = mapped_column(String(160))
    scenario_type: Mapped[str] = mapped_column(String(40))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    affected_shipments: Mapped[list[str]] = mapped_column(JSON, default=list)
    impact_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    total_cargo_at_risk_usd: Mapped[float] = mapped_column(Float)
    estimated_delay_hours_avg: Mapped[float] = mapped_column(Float)
    alternative_routes_count: Mapped[int] = mapped_column(Integer)
    cost_of_disruption_usd: Mapped[float] = mapped_column(Float)
    gemini_analysis: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(40), default="pending")


class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(120))
    industry: Mapped[str] = mapped_column(String(80))
    risk_score: Mapped[float] = mapped_column(Float)
    on_time_rate: Mapped[float] = mapped_column(Float)
    avg_lead_time_days: Mapped[float] = mapped_column(Float)
    alternative_supplier_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    geopolitical_risk: Mapped[float] = mapped_column(Float)
    financial_stability: Mapped[str] = mapped_column(String(40))
    active_shipments_count: Mapped[int] = mapped_column(Integer, default=0)
    last_incident_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinancialImpact(Base):
    __tablename__ = "financial_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disruption_id: Mapped[str] = mapped_column(String(20), ForeignKey("disruptions.id"))
    shipment_id: Mapped[str] = mapped_column(String(20), ForeignKey("shipments.id"))
    delay_hours: Mapped[float] = mapped_column(Float)
    delay_cost_usd: Mapped[float] = mapped_column(Float)
    cargo_at_risk_usd: Mapped[float] = mapped_column(Float)
    rerouting_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_impact_usd: Mapped[float] = mapped_column(Float)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Index("ix_shipments_risk_status", Shipment.risk_level, Shipment.status)
Index("ix_shipments_client_risk", Shipment.client_id, Shipment.risk_level)
Index("ix_disruptions_active_severity", Disruption.active, Disruption.severity)
Index("ix_alerts_priority_ack", Alert.priority, Alert.acknowledged)
Index("ix_external_risks_active_severity", ExternalRiskEvent.active, ExternalRiskEvent.severity)
Index("ix_intelligence_scans_created", IntelligenceScan.created_at)
