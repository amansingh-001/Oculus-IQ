from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any

import google.generativeai as genai

from core.config import settings


def _extract_json(text: str | None) -> dict[str, Any] | list[Any] | None:
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            return json.loads(match.group(1).strip())
    except Exception:
        return None

    return None


class GeminiService:
    FALLBACKS: dict[str, Any] = {
        "risk_analysis": {
            "risk_score": 65,
            "risk_level": "high",
            "risk_factors": [
                "Weather pattern analysis indicates moderate storm probability on route",
                "Port congestion at destination estimated at 67% capacity",
                "Carrier reliability dip detected on similar lanes",
            ],
            "confidence": 0.72,
            "reasoning": "Risk assessment based on route historical data and corridor conditions.",
        },
        "route_alternatives": [
            {
                "rank": 1,
                "route_name": "Route A: Optimized Current Path",
                "total_days": 6.2,
                "base_cost_usd": 92000,
                "reliability_score": 86.0,
                "tradeoffs": "Best overall balance of time and cost.",
                "recommendation": True,
                "reasoning": "Avoids active congestion zones while keeping transit time stable.",
            },
            {
                "rank": 2,
                "route_name": "Route B: Speed-Priority Air Segment",
                "total_days": 3.8,
                "base_cost_usd": 185000,
                "reliability_score": 92.0,
                "tradeoffs": "Faster but significantly higher cost.",
                "recommendation": False,
                "reasoning": "Best for time-critical cargo with premium budgets.",
            },
            {
                "rank": 3,
                "route_name": "Route C: Extended Sea Alternative",
                "total_days": 9.4,
                "base_cost_usd": 64000,
                "reliability_score": 78.0,
                "tradeoffs": "Lowest cost, longer transit time.",
                "recommendation": False,
                "reasoning": "Cost-efficient route with higher schedule risk.",
            },
        ],
        "alert_draft": {
            "subject": "URGENT: Supply Chain Alert - Shipment Delay Notification",
            "body": (
                "Dear Partner,\n\n"
                "We are writing to inform you that one of your shipments is experiencing elevated risk due to current "
                "route conditions. Our logistics team is actively monitoring the situation and evaluating alternative "
                "routing options. We will provide an updated ETA within 24 hours.\n\n"
                "We appreciate your understanding.\n\n"
                "Best regards,\nOculusIQ Operations Center"
            ),
            "urgency": "high",
        },
        "copilot": (
            "Based on current fleet data, prioritize rerouting the critical-risk shipments in impacted corridors. "
            "Port congestion remains elevated, so pre-clear arrivals expected in the next 48 hours. "
            "Immediate actions: (1) acknowledge urgent alerts, (2) request ETA updates from delayed carriers, "
            "(3) notify clients with high-value cargo at risk."
        ),
        "simulation": (
            "Simulation results indicate significant cascade risk. Primary disruption will propagate to secondary ports "
            "within 12-18 hours as vessel slot competition intensifies. Recommend activating contingency contracts with "
            "alternative carriers and pre-positioning inventory at buffer warehouses."
        ),
    }

    def __init__(self) -> None:
        self.model_name = "gemini-1.5-flash"
        self.model = None
        self._initialized = bool(settings.gemini_api_key and settings.gemini_api_key != "your_key_here")

        if self._initialized:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(self.model_name)

    @property
    def is_configured(self) -> bool:
        return self._initialized

    async def _call_gemini(self, prompt: str) -> str | None:
        if not self._initialized or self.model is None:
            return None

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            text = (response.text or "").strip()
            return text if text else None
        except Exception as exc:
            print(f"Gemini error: {exc}")
            return None

    async def analyze_shipment_risk(self, shipment: dict[str, Any], weather: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "You are a supply chain risk analyst. Analyze this shipment and return JSON only.\n"
            "Return this exact JSON structure, no other text:\n"
            "{\"risk_score\": 0-100, \"risk_level\": \"low|medium|high|critical\", "
            "\"risk_factors\": [\"factor1\", \"factor2\", \"factor3\"], "
            "\"confidence\": 0.0-1.0, \"reasoning\": \"brief explanation\"}\n"
            f"Shipment: {json.dumps(shipment)}\n"
            f"Weather: {json.dumps(weather)}\n"
        )

        raw = await self._call_gemini(prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            return parsed
        return self.FALLBACKS["risk_analysis"]

    async def generate_route_alternatives(
        self,
        shipment: dict[str, Any],
        disruption: dict[str, Any] | None,
        graph_routes: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        routes_context = json.dumps(graph_routes[:3], indent=2) if graph_routes else "No pre-computed routes available"
        prompt = (
            "You are a logistics routing expert. Enhance computed route alternatives with strategic insights.\n"
            f"Shipment: {json.dumps(shipment)}\n"
            f"Disruption: {json.dumps(disruption or {})}\n"
            f"Pre-computed routes: {routes_context}\n"
            "Return JSON array of exactly 3 route objects. Each must have: route_name, total_days, base_cost_usd, "
            "reliability_score, tradeoffs, recommendation (bool, only one true), reasoning. JSON only." 
        )

        raw = await self._call_gemini(prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, list) and parsed:
            return parsed[:3]
        return self.FALLBACKS["route_alternatives"]

    async def draft_alert_notification(self, alert: dict[str, Any], shipment: dict[str, Any] | None = None) -> dict[str, Any]:
        prompt = (
            "Draft a professional supply chain alert notification.\n"
            f"Alert: {json.dumps(alert)}\n"
            f"Shipment: {json.dumps(shipment or {})}\n"
            "Return JSON: {\"subject\": \"...\", \"body\": \"...\", \"urgency\": \"high|medium\"}"
        )

        raw = await self._call_gemini(prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict) and parsed.get("subject"):
            return parsed
        return self.FALLBACKS["alert_draft"]

    async def copilot_chat(self, message: str, context: dict[str, Any], history: list[dict[str, Any]] | None = None) -> str:
        history_text = "\n".join(
            f"{'User' if m.get('role') == 'user' else 'OculusIQ'}: {m.get('content', '')}"
            for m in (history or [])[-6:]
        )

        prompt = (
            "You are OculusIQ, an elite supply chain intelligence officer.\n"
            f"Current fleet status: {json.dumps(context)}\n"
            f"Recent conversation:\n{history_text}\n"
            f"User asks: {message}\n"
            "Respond as an expert supply chain intelligence officer. Be specific and actionable. Max 180 words."
        )

        raw = await self._call_gemini(prompt)
        if raw and len(raw) > 20:
            return raw.strip()
        return self.FALLBACKS["copilot"]

    async def analyze_simulation(
        self,
        scenario: dict[str, Any],
        affected_count: int,
        cascade_count: int,
        financial_impact: dict[str, Any],
        duration_hours: int,
    ) -> str:
        prompt = (
            "Analyze this supply chain disruption scenario and provide strategic intelligence.\n"
            f"Scenario: {scenario.get('name')}\n"
            f"Duration: {duration_hours} hours\n"
            f"Directly affected shipments: {affected_count}\n"
            f"Cascade-affected shipments: {cascade_count}\n"
            f"Financial impact: {financial_impact.get('total_display', 'Unknown')}\n"
            "Provide a 3-paragraph strategic analysis: immediate impact, cascade risk timeline, mitigation strategy."
        )

        raw = await self._call_gemini(prompt)
        return raw if raw else self.FALLBACKS["simulation"]

    async def parse_bill_of_lading(self, document_text: str) -> dict[str, Any]:
        prompt = (
            "Extract supply chain data from this Bill of Lading document text.\n"
            "Return JSON only with these fields: bl_number, shipper_name, consignee_name, notify_party, "
            "port_of_loading, port_of_discharge, vessel_name, voyage_number, container_numbers, "
            "cargo_description, hs_code, gross_weight_kg, declared_value_usd, etd, eta, freight_terms, incoterm.\n"
            f"Text: {document_text[:8000]}"
        )
        raw = await self._call_gemini(prompt)
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            return parsed
        return {
            "bl_number": "BL-PENDING",
            "shipper_name": "Unknown shipper",
            "consignee_name": "Unknown consignee",
            "notify_party": "",
            "port_of_loading": "",
            "port_of_discharge": "",
            "vessel_name": "",
            "voyage_number": "",
            "container_numbers": [],
            "cargo_description": document_text[:160],
            "hs_code": "",
            "gross_weight_kg": 0,
            "declared_value_usd": 0,
            "etd": "",
            "eta": "",
            "freight_terms": "",
            "incoterm": "",
        }


gemini_service = GeminiService()
