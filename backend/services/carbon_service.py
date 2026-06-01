from __future__ import annotations

from typing import Any


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


class CarbonFootprintTracker:
    EMISSION_FACTORS = {
        "sea": 0.016,
        "rail": 0.028,
        "road": 0.096,
        "air": 0.602,
        "multimodal": 0.055,
    }
    EU_COUNTRIES = {"Germany", "France", "Netherlands", "Belgium", "Italy", "Spain"}

    def calculate_shipment_carbon(self, shipment: Any) -> dict[str, Any]:
        distance_km = float(_get(shipment, "route_distance_km", 15_000) or 15_000)
        weight_kg = float(_get(shipment, "weight_kg", 20_000) or 20_000)
        mode = str(_get(shipment, "mode", "sea") or "sea")
        factor = self.EMISSION_FACTORS.get(mode, self.EMISSION_FACTORS["sea"])
        weight_tonnes = weight_kg / 1000
        co2_kg = distance_km * weight_tonnes * factor
        co2_tonnes = co2_kg / 1000
        dest_country = str(_get(shipment, "dest_country", "") or "")
        cbam_cost = co2_tonnes * 50 if dest_country in self.EU_COUNTRIES else 0

        return {
            "co2_kg": round(co2_kg, 1),
            "co2_tonnes": round(co2_tonnes, 3),
            "mode": mode,
            "distance_km": round(distance_km, 1),
            "weight_kg": round(weight_kg, 1),
            "cbam_cost_eur": round(cbam_cost, 2),
            "equivalent_trees": round(co2_tonnes * 45),
            "vs_air_comparison": "Sea freight emits 38x less CO2 than air for this route",
        }

    def compare_route_carbon(self, alternatives: list[dict[str, Any]], shipment: Any) -> list[dict[str, Any]]:
        enriched = []
        for route in alternatives:
            modes = route.get("modes") or []
            route_shipment = {
                "mode": route.get("primary_mode") or (modes[0] if modes else _get(shipment, "mode", "sea")),
                "route_distance_km": route.get("distance_km") or _get(shipment, "route_distance_km", 15_000),
                "weight_kg": _get(shipment, "weight_kg", 20_000),
                "dest_country": _get(shipment, "dest_country", ""),
            }
            route_payload = dict(route)
            route_payload["carbon"] = self.calculate_shipment_carbon(route_shipment)
            enriched.append(route_payload)
        return enriched


carbon_tracker = CarbonFootprintTracker()
