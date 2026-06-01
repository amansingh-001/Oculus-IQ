"""Digital Twin — What-If Simulation Engine."""
from __future__ import annotations

import math
import random
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Shipment, SimulationRun
from services.gemini_service import gemini_service


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DigitalTwinEngine:
    """Runs parallel universe simulations of the supply chain."""

    SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
        "suez_closure": {
            "name": "Suez Canal Closure",
            "description": "Complete closure of Suez Canal (Red Sea conflict escalation)",
            "affected_region": {"lat": 30.58, "lon": 32.26, "radius_km": 1100},
            "affected_ports": ["SUEZ_CANAL"],
            "severity": "critical",
            "duration_hours_options": [24, 48, 96, 168, 720],
            "reroute_via": "Cape of Good Hope",
            "reroute_extra_days": 14,
            "historical_precedent": "2024 Red Sea Crisis",
        },
        "typhoon_south_china_sea": {
            "name": "Category 4 Typhoon — South China Sea",
            "description": "Major typhoon impacting key Asian shipping lanes",
            "affected_region": {"lat": 18.0, "lon": 115.0, "radius_km": 800},
            "affected_ports": ["CNSHA", "HKGHK", "SGSIN", "CNSZN"],
            "severity": "high",
            "duration_hours_options": [12, 24, 48, 72],
            "historical_precedent": "Typhoon Mangkhut 2018",
        },
        "shanghai_lockdown": {
            "name": "Shanghai Port Partial Lockdown",
            "description": "Public health or security event causing partial port closure",
            "affected_region": {"lat": 31.23, "lon": 121.47, "radius_km": 350},
            "affected_ports": ["CNSHA"],
            "capacity_reduction_pct": 60,
            "severity": "critical",
            "duration_hours_options": [168, 336, 720],
            "historical_precedent": "COVID Shanghai 2022",
        },
        "rotterdam_strike": {
            "name": "Rotterdam Dock Workers Strike",
            "description": "Industrial action at major European ports",
            "affected_region": {"lat": 51.90, "lon": 4.47, "radius_km": 500},
            "affected_ports": ["NLRTM", "DEHAM", "BEANR"],
            "capacity_reduction_pct": 100,
            "severity": "high",
            "duration_hours_options": [24, 72, 168],
            "historical_precedent": "European Port Strikes 2023",
        },
        "global_fuel_shortage": {
            "name": "Global Bunker Fuel Shortage",
            "description": "OPEC supply cut driving fuel cost surge",
            "affected_region": None,
            "affected_ports": [],
            "cost_increase_pct": 40,
            "speed_reduction_pct": 20,
            "severity": "medium",
            "duration_hours_options": [720, 2160],
            "historical_precedent": "2022 Fuel Cost Spike",
        },
        "cyber_attack_logistics": {
            "name": "Ransomware Attack on Major Carrier",
            "description": "Critical IT systems compromised at major shipping line",
            "affected_region": None,
            "affected_carriers": ["Maersk", "MSC"],
            "booking_freeze_hours": 48,
            "severity": "high",
            "duration_hours_options": [24, 48, 96],
            "historical_precedent": "NotPetya Maersk 2017",
        },
    }

    async def get_scenarios(self) -> list[dict[str, Any]]:
        """Return available scenario templates."""
        scenarios = []
        for key, s in self.SCENARIO_TEMPLATES.items():
            scenarios.append({
                "key": key,
                "name": s["name"],
                "description": s.get("description", ""),
                "severity": s["severity"],
                "duration_options": s.get("duration_hours_options", [48]),
                "historical_precedent": s.get("historical_precedent"),
                "affected_ports": s.get("affected_ports", []),
            })
        return scenarios

    async def run_simulation(
        self, scenario_key: str, duration_hours: int, db: AsyncSession, target: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        scenario = self.SCENARIO_TEMPLATES.get(scenario_key)
        if not scenario:
            return {"error": f"Unknown scenario: {scenario_key}"}
        scenario = dict(scenario)
        target = target or {"target_type": "all"}
        if target.get("severity"):
            scenario["severity"] = target["severity"]

        sim_id = f"SIM-{str(uuid.uuid4())[:8]}"

        # Fetch all shipments
        result = await db.execute(
            select(Shipment).where(Shipment.status.in_(["in_transit", "delayed", "pending"]))
        )
        all_shipments = result.scalars().all()
        target_shipments = self._filter_target_shipments(all_shipments, target)
        if target.get("target_type") not in {None, "", "all"} and not target_shipments:
            return {"error": "No active cargo matched the selected target."}

        # Step 1: Find directly affected
        directly_affected = self._find_affected(target_shipments, scenario)

        # Step 2: Cascade analysis
        cascade = self._calculate_cascade(directly_affected, all_shipments, scenario, duration_hours)

        # Step 3: Financial impact
        financial = self._calculate_financial_impact(cascade, scenario, len(directly_affected))

        # Step 4: Strategic options
        strategic = self._generate_strategic_options(scenario, len(directly_affected), cascade)

        # Step 5: Gemini analysis
        gemini_text = await gemini_service.analyze_simulation(
            scenario=scenario,
            affected_count=len(directly_affected),
            cascade_count=cascade["secondary_affected_count"],
            financial_impact=financial,
            duration_hours=duration_hours,
        )

        sim_result = {
            "simulation_id": sim_id,
            "scenario": scenario["name"],
            "scenario_key": scenario_key,
            "duration_hours": duration_hours,
            "status": "complete",
            "target_impact": self._target_impact(target, target_shipments, directly_affected),
            "primary_impact": {
                "shipments_directly_affected": len(directly_affected),
                "shipment_ids": [s.id for s in directly_affected[:20]],
                "avg_delay_hours": cascade["avg_primary_delay_hours"],
                "total_teu_affected": len(directly_affected) * random.randint(1, 4),
            },
            "cascade_impact": {
                "secondary_shipments_affected": cascade["secondary_affected_count"],
                "tertiary_ripple_count": cascade["tertiary_count"],
                "port_overflow_risk": cascade["port_overflow_risk"],
                "cascade_delay_hours": cascade["avg_cascade_delay_hours"],
                "cascade_severity": cascade["severity"],
            },
            "financial_impact": financial,
            "strategic_options": strategic,
            "gemini_analysis": gemini_text,
            "map_visualization": {
                "affected_region": scenario.get("affected_region"),
                "affected_ports": scenario.get("affected_ports", []),
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        # Persist
        sim_run = SimulationRun(
            id=sim_id,
            scenario_name=scenario["name"],
            scenario_type="what_if",
            parameters={"scenario_key": scenario_key, "duration_hours": duration_hours, "target": target},
            affected_shipments=[s.id for s in directly_affected[:50]],
            impact_analysis=sim_result,
            total_cargo_at_risk_usd=financial["total_estimated_impact_usd"],
            estimated_delay_hours_avg=cascade["avg_primary_delay_hours"],
            alternative_routes_count=len(directly_affected),
            cost_of_disruption_usd=financial["total_estimated_impact_usd"],
            gemini_analysis=gemini_text,
            status="complete",
        )
        db.add(sim_run)
        await db.commit()

        return sim_result

    def _filter_target_shipments(self, shipments: list, target: dict[str, Any]) -> list:
        target_type = target.get("target_type") or "all"
        if target_type == "client" and target.get("client_id"):
            return [shipment for shipment in shipments if shipment.client_id == target["client_id"]]
        if target_type == "shipment" and target.get("shipment_id"):
            return [shipment for shipment in shipments if shipment.id == target["shipment_id"]]
        if target_type == "operator" and target.get("operator_name"):
            operator = str(target["operator_name"]).lower()
            return [
                shipment
                for shipment in shipments
                if operator in ((shipment.operator_name or shipment.carrier or "").lower())
            ]
        return shipments

    def _target_impact(self, target: dict[str, Any], target_shipments: list, directly_affected: list) -> dict[str, Any]:
        cargo_value = sum(float(shipment.cargo_value_usd or 0) for shipment in directly_affected)
        affected_ids = {shipment.id for shipment in directly_affected}
        at_risk = [shipment for shipment in target_shipments if shipment.risk_score >= 60 or shipment.id in affected_ids]
        sla_impact = "critical" if len(directly_affected) >= 10 else "high" if directly_affected else "low"
        return {
            "target_type": target.get("target_type") or "all",
            "target_ref": target.get("client_id") or target.get("shipment_id") or target.get("operator_name") or "all",
            "target_shipments": len(target_shipments),
            "affected_target_shipments": len(directly_affected),
            "at_risk_target_shipments": len(at_risk),
            "target_cargo_value_at_risk_usd": round(cargo_value),
            "sla_impact": sla_impact,
            "recommended_actions": [
                "Pre-brief account owner with the target-specific exposure summary",
                "Prioritize tracking updates for affected cargo IDs",
                "Prepare rerouting or carrier escalation if SLA impact remains high",
            ],
        }

    def _find_affected(self, shipments: list, scenario: dict) -> list:
        affected = []
        region = scenario.get("affected_region")
        affected_carriers = scenario.get("affected_carriers", [])

        for s in shipments:
            if region:
                dist = _haversine_km(s.current_lat, s.current_lon, region["lat"], region["lon"])
                if dist <= region["radius_km"]:
                    affected.append(s)
                    continue
            if affected_carriers and s.carrier in affected_carriers:
                affected.append(s)

        # For global scenarios with no region, affect a percentage
        if not region and not affected_carriers:
            sample_count = min(len(shipments), max(1 if shipments else 0, int(len(shipments) * 0.3)))
            affected = random.sample(shipments, sample_count)

        return affected

    def _calculate_cascade(self, directly_affected: list, all_shipments: list, scenario: dict, duration_hours: int) -> dict:
        primary_count = len(directly_affected)
        avg_primary_delay = min(duration_hours * 0.6, 120)

        # Secondary: shipments at same ports arriving within window
        affected_cities = set()
        for s in directly_affected:
            affected_cities.add(s.dest_city)
            affected_cities.add(s.origin_city)

        secondary_count = 0
        for s in all_shipments:
            if s not in directly_affected:
                if s.dest_city in affected_cities or s.origin_city in affected_cities:
                    secondary_count += 1

        secondary_count = min(secondary_count, int(primary_count * 1.8))
        tertiary_count = int(secondary_count * 0.4)

        severity_map = {"critical": "critical", "high": "high", "medium": "medium"}
        sev = severity_map.get(scenario.get("severity", "medium"), "medium")

        return {
            "primary_count": primary_count,
            "secondary_affected_count": secondary_count,
            "tertiary_count": tertiary_count,
            "avg_primary_delay_hours": round(avg_primary_delay, 1),
            "avg_cascade_delay_hours": round(avg_primary_delay * 0.4, 1),
            "port_overflow_risk": "high" if primary_count > 30 else "medium" if primary_count > 10 else "low",
            "severity": sev,
            "reroutable_count": int(primary_count * 0.6),
        }

    def _calculate_financial_impact(self, cascade: dict, scenario: dict, directly_affected_count: int) -> dict:
        avg_cargo_value = 350_000
        delay_cost = (cascade["avg_primary_delay_hours"] / 24) * avg_cargo_value * 0.002 * directly_affected_count
        rerouting_cost = cascade.get("reroutable_count", 0) * 15_000
        insurance_spike = avg_cargo_value * directly_affected_count * 0.001
        penalty_cost = directly_affected_count * 5_000 * 0.3
        total = delay_cost + rerouting_cost + insurance_spike + penalty_cost

        return {
            "delay_cost_usd": round(delay_cost),
            "rerouting_cost_usd": round(rerouting_cost),
            "insurance_spike_usd": round(insurance_spike),
            "penalty_clauses_usd": round(penalty_cost),
            "total_estimated_impact_usd": round(total),
            "total_display": f"${total / 1_000_000:.1f}M" if total > 1_000_000 else f"${total / 1000:.0f}K",
        }

    def _generate_strategic_options(self, scenario: dict, affected_count: int, cascade: dict) -> list[dict]:
        options = [
            {"priority": "urgent", "action": "Activate contingency routing protocols for all affected shipments",
             "impact": f"Protects {affected_count} shipments from primary delay"},
            {"priority": "high", "action": "Pre-notify all clients with cargo in affected corridors",
             "impact": "Reduces SLA penalty exposure by 60%"},
            {"priority": "high", "action": "Engage backup carrier contracts for rerouting",
             "impact": f"Can reroute {cascade.get('reroutable_count', 0)} shipments within 24h"},
        ]
        if scenario.get("reroute_via"):
            options.append({
                "priority": "medium",
                "action": f"Evaluate reroute via {scenario['reroute_via']}",
                "impact": f"Adds ~{scenario.get('reroute_extra_days', 7)} days but avoids disruption zone",
            })
        options.append({
            "priority": "medium",
            "action": "Deploy autonomous monitoring for cascade detection",
            "impact": f"Early warning for {cascade['secondary_affected_count']} secondary-affected shipments",
        })
        return options

    async def get_history(self, db: AsyncSession) -> list[dict[str, Any]]:
        result = await db.execute(
            select(SimulationRun).order_by(SimulationRun.created_at.desc()).limit(20)
        )
        runs = result.scalars().all()
        return [
            {
                "simulation_id": r.id,
                "scenario_name": r.scenario_name,
                "status": r.status,
                "total_impact_usd": r.cost_of_disruption_usd,
                "affected_shipments": len(r.affected_shipments or []),
                "delay_hours_avg": r.estimated_delay_hours_avg,
                "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            }
            for r in runs
        ]

    async def get_simulation(self, sim_id: str, db: AsyncSession) -> dict[str, Any] | None:
        run = await db.get(SimulationRun, sim_id)
        if not run:
            return None
        return run.impact_analysis or {"simulation_id": run.id, "status": run.status}


simulation_engine = DigitalTwinEngine()
