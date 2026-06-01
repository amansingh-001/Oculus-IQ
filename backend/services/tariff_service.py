from __future__ import annotations

from typing import Any


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


class TariffImpactEngine:
    TARIFF_MATRIX = {
        ("China", "United States", "8"): 145.0,
        ("China", "United States", "6"): 25.0,
        ("China", "United States", "7"): 35.0,
        ("India", "United States", "6"): 0.0,
        ("India", "United States", "3"): 2.5,
        ("India", "EU", "30"): 0.0,
        ("India", "United Arab Emirates", "8"): 0.0,
        ("United Arab Emirates", "EU", "8"): 3.0,
        ("Vietnam", "United States", "8"): 0.0,
        ("Bangladesh", "EU", "6"): 0.0,
        ("Turkey", "United States", "6"): 8.0,
        ("Singapore", "United Kingdom", "8"): 2.0,
        ("Indonesia", "Australia", "2"): 4.0,
    }

    CBAM_PRODUCTS = {"72", "76", "28", "31", "38"}
    EU_COUNTRIES = {"Germany", "France", "Netherlands", "Belgium", "Italy", "Spain"}

    def _destination_key(self, dest_country: str) -> str:
        return "EU" if dest_country in self.EU_COUNTRIES else dest_country

    def calculate_landed_cost(self, shipment: Any) -> dict[str, Any]:
        cargo_value = float(_get(shipment, "cargo_value_usd", 100_000) or 100_000)
        distance_km = float(_get(shipment, "route_distance_km", 12_000) or 12_000)
        mode = str(_get(shipment, "mode", "sea") or "sea")
        freight_factor = {"sea": 0.18, "air": 1.35, "rail": 0.25, "road": 0.3, "multimodal": 0.38}.get(mode, 0.22)
        freight_cost = float(_get(shipment, "base_cost_usd", 0) or 0) or max(2_000, distance_km * freight_factor)

        hs_code = str(_get(shipment, "hs_code", "000000") or "000000")
        hs_prefix_1 = hs_code[:1]
        hs_prefix_2 = hs_code[:2]
        origin = str(_get(shipment, "origin_country", "Unknown") or "Unknown")
        dest = str(_get(shipment, "dest_country", "Unknown") or "Unknown")
        dest_key = self._destination_key(dest)

        tariff_rate = self.TARIFF_MATRIX.get((origin, dest, hs_prefix_1))
        if tariff_rate is None:
            tariff_rate = self.TARIFF_MATRIX.get((origin, dest_key, hs_prefix_2))
        if tariff_rate is None:
            tariff_rate = self.TARIFF_MATRIX.get((origin, dest_key, hs_prefix_1), 5.0)

        tariff_amount = cargo_value * (tariff_rate / 100)
        cbam_surcharge = cargo_value * 0.05 if dest in self.EU_COUNTRIES and hs_prefix_2 in self.CBAM_PRODUCTS else 0
        insurance = cargo_value * 0.005
        handling = freight_cost * 0.15
        total_landed = freight_cost + tariff_amount + cbam_surcharge + insurance + handling

        return {
            "freight_cost_usd": round(freight_cost),
            "cargo_value_usd": round(cargo_value),
            "tariff_rate_pct": round(tariff_rate, 2),
            "tariff_amount_usd": round(tariff_amount),
            "cbam_surcharge_usd": round(cbam_surcharge),
            "insurance_usd": round(insurance),
            "handling_fees_usd": round(handling),
            "total_landed_cost_usd": round(total_landed),
            "tariff_flag": tariff_rate > 20,
            "cbam_applicable": cbam_surcharge > 0,
        }

    def compare_route_tariffs(self, shipment: Any, alternative_routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base_cost = self.calculate_landed_cost(shipment)
        origin = _get(shipment, "origin_country", "Unknown")

        enriched = []
        for route in alternative_routes:
            waypoint_text = " ".join(
                str(point.get("name") or point.get("country") or point.get("id") or point)
                for point in route.get("waypoints", [])
            )
            adjusted_origin = "United Arab Emirates" if "Dubai" in waypoint_text or "UAE" in waypoint_text else origin
            adjusted_shipment = {
                "cargo_value_usd": _get(shipment, "cargo_value_usd", 100_000),
                "origin_country": adjusted_origin,
                "dest_country": _get(shipment, "dest_country", "Unknown"),
                "hs_code": _get(shipment, "hs_code", "000000"),
                "base_cost_usd": route.get("base_cost_usd") or route.get("cost"),
                "route_distance_km": route.get("distance_km") or _get(shipment, "route_distance_km", 12_000),
                "mode": route.get("primary_mode") or (route.get("modes") or [_get(shipment, "mode", "sea")])[0],
            }
            route_payload = dict(route)
            route_payload["origin_country_adjusted"] = adjusted_origin
            route_payload["landed_cost_analysis"] = self.calculate_landed_cost(adjusted_shipment)
            route_payload["tariff_savings_vs_current"] = (
                base_cost["tariff_amount_usd"] - route_payload["landed_cost_analysis"]["tariff_amount_usd"]
            )
            route_payload["total_savings_vs_current"] = (
                base_cost["total_landed_cost_usd"] - route_payload["landed_cost_analysis"]["total_landed_cost_usd"]
            )
            enriched.append(route_payload)
        return enriched


tariff_engine = TariffImpactEngine()
