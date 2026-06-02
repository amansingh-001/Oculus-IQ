from __future__ import annotations

from datetime import datetime
from typing import Any


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def risk_level_for_score(score: int) -> str:
    if score <= 25:
        return "low"
    if score <= 50:
        return "medium"
    if score <= 75:
        return "high"
    return "critical"


class RiskEngine:
    carrier_delay_rates = {
        "Maersk": 5,
        "MSC": 8,
        "COSCO": 12,
        "CMA CGM": 10,
        "Hapag-Lloyd": 9,
        "Evergreen": 7,
        "DHL": 4,
        "FedEx": 5,
        "UPS": 6,
        "Emirates SkyCargo": 3,
    }

    cargo_sensitivity = {
        "Pharmaceuticals": 15,
        "Electronics": 10,
        "Automotive Parts": 8,
        "Textiles": 5,
        "Chemicals": 12,
        "Food": 9,
    }

    asia_pacific_countries = {
        "China",
        "India",
        "Singapore",
        "Japan",
        "Australia",
        "Indonesia",
        "Vietnam",
        "Malaysia",
        "South Korea",
    }

    def calculate_risk(
        self,
        shipment: dict | Any,
        weather_data: dict | None = None,
        disruption: dict | Any | None = None,
    ) -> dict[str, Any]:
        factors: list[str] = []
        score = 0

        # Weather severity (up to 35)
        weather_data = weather_data or {}
        wind_kmh = float(weather_data.get("wind_kmh", 0.0) or 0.0)
        weather_level = weather_data.get("risk_level", "low")

        if weather_level == "high" or wind_kmh > 70:
            score += 35
            factors.append("Severe weather detected along current route")
        elif weather_level == "medium" or wind_kmh > 50:
            score += 25
            factors.append("Elevated weather risk with high winds")
        elif weather_level == "low" and wind_kmh > 30:
            score += 8
            factors.append("Mild weather turbulence on route")

        # Route type risk (up to 20)
        origin_country = _get(shipment, "origin_country", "")
        dest_country = _get(shipment, "dest_country", "")
        mode = _get(shipment, "mode", "sea")

        if mode == "sea" and origin_country in self.asia_pacific_countries and dest_country in {
            "Netherlands",
            "Germany",
            "United Kingdom",
        }:
            score += 15
            factors.append("Route likely crosses Suez-linked maritime corridors")
        elif mode == "sea" and origin_country in self.asia_pacific_countries:
            score += 10
            factors.append("South China Sea/Pacific shipping corridor exposure")

        # Historical carrier delay rate (up to 20)
        carrier = _get(shipment, "carrier", "")
        delay_rate = self.carrier_delay_rates.get(carrier, 7)
        delay_score = min(20, int(delay_rate * 1.8))
        score += delay_score
        factors.append(f"Carrier historical delay rate contributes +{delay_score} risk points")

        # Cargo sensitivity (up to 15)
        cargo_type = _get(shipment, "cargo_type", "Electronics")
        cargo_score = self.cargo_sensitivity.get(cargo_type, 7)
        score += cargo_score
        if cargo_score >= 12:
            factors.append("Cargo type is highly sensitive to schedule disruptions")

        # Seasonal risk (up to 10)
        month = datetime.utcnow().month
        if month in {4, 5, 6, 7, 8, 9, 10, 11} and mode == "sea" and origin_country in self.asia_pacific_countries:
            score += 10
            factors.append("Typhoon/cyclone season increases lane volatility")

        # Disruption severity adjustment
        if disruption is not None:
            severity = _get(disruption, "severity", "low")
            if severity == "critical":
                score += 15
                factors.append("Critical disruption actively impacting this route")
            elif severity == "high":
                score += 10
                factors.append("High-severity disruption impacts transit reliability")
            elif severity == "medium":
                score += 5

        score = max(0, min(100, score))
        risk_level = risk_level_for_score(score)

        if not factors:
            factors.append("No major disruption signals detected")

        return {
            "risk_score": score,
            "risk_level": risk_level,
            "risk_factors": factors[:5],
            "confidence": 0.82,
            "reasoning": "Rule-based aggregate score from weather, route, carrier, cargo, and seasonality.",
        }
