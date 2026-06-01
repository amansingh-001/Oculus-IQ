"""Graph-based route optimization engine with Dijkstra / Yen's K-shortest paths."""
from __future__ import annotations

import heapq
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import PortNode, RouteEdge
from services.gemini_service import gemini_service
from services.port_service import port_congestion_engine


class RouteGraph:
    """Directed weighted graph of the global shipping network."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.adjacency: dict[str, list[dict[str, Any]]] = {}

    async def load_from_db(self, db: AsyncSession) -> None:
        port_result = await db.execute(select(PortNode))
        ports = port_result.scalars().all()

        edge_result = await db.execute(select(RouteEdge).where(RouteEdge.is_active.is_(True)))
        edges = edge_result.scalars().all()

        self.nodes.clear()
        self.adjacency.clear()

        for p in ports:
            self.nodes[p.id] = {
                "id": p.id, "name": p.name, "city": p.city, "country": p.country,
                "lat": p.lat, "lon": p.lon, "type": p.type,
                "capacity_teu": p.capacity_teu,
                "congestion_score": p.congestion_score,
            }
            self.adjacency[p.id] = []

        for e in edges:
            if e.from_port_id in self.adjacency:
                self.adjacency[e.from_port_id].append({
                    "to": e.to_port_id,
                    "mode": e.mode,
                    "distance_km": e.distance_km,
                    "base_hours": e.base_transit_hours,
                    "base_cost": e.base_cost_usd_per_teu,
                    "delay_factor": e.current_delay_factor,
                    "reliability": e.reliability_score,
                })

    def _edge_weight(self, edge: dict, optimize_for: str = "balanced") -> float:
        time_score = edge["base_hours"] * edge["delay_factor"]
        cost_score = edge["base_cost"] / 1000
        reliability_penalty = (100 - edge["reliability"]) * 2

        if optimize_for == "time":
            return time_score * 2 + cost_score * 0.5 + reliability_penalty
        elif optimize_for == "cost":
            return cost_score * 2 + time_score * 0.5 + reliability_penalty
        elif optimize_for == "reliability":
            return reliability_penalty * 3 + time_score + cost_score * 0.5
        return time_score + cost_score + reliability_penalty  # balanced

    def _dijkstra(
        self, origin: str, dest: str,
        blocked_ports: list[str] | None = None,
        optimize_for: str = "balanced",
    ) -> list[str] | None:
        """Standard Dijkstra returning shortest path as list of port IDs."""
        blocked = set(blocked_ports or [])
        dist: dict[str, float] = {origin: 0}
        prev: dict[str, str | None] = {origin: None}
        heap = [(0, origin)]
        visited: set[str] = set()

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)

            if u == dest:
                # Reconstruct path
                path: list[str] = []
                node: str | None = u
                while node is not None:
                    path.append(node)
                    node = prev.get(node)
                return list(reversed(path))

            for edge in self.adjacency.get(u, []):
                v = edge["to"]
                if v in visited or v in blocked:
                    continue
                w = self._edge_weight(edge, optimize_for)
                new_dist = d + w
                if new_dist < dist.get(v, float("inf")):
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(heap, (new_dist, v))

        return None

    def _get_edge_data(self, from_id: str, to_id: str) -> dict[str, Any] | None:
        for edge in self.adjacency.get(from_id, []):
            if edge["to"] == to_id:
                return edge
        return None

    def find_k_shortest(
        self, origin: str, dest: str, k: int = 3,
        blocked_ports: list[str] | None = None,
        optimize_for: str = "balanced",
    ) -> list[dict[str, Any]]:
        """Find k shortest paths using Yen's algorithm."""
        shortest = self._dijkstra(origin, dest, blocked_ports, optimize_for)
        if not shortest:
            return []

        confirmed: list[list[str]] = [shortest]
        candidates: list[tuple[float, list[str]]] = []

        for i in range(1, k):
            for j in range(len(confirmed[-1]) - 1):
                spur_node = confirmed[-1][j]
                root_path = confirmed[-1][:j + 1]

                edges_to_remove: list[tuple[str, str]] = []
                for path in confirmed:
                    if len(path) > j and path[:j + 1] == root_path:
                        edges_to_remove.append((path[j], path[j + 1]))

                # Temporarily block edges
                blocked = set(blocked_ports or [])
                for node in root_path[:-1]:
                    blocked.add(node)
                blocked.discard(spur_node)
                blocked.discard(origin)

                spur_path = self._dijkstra(spur_node, dest, list(blocked), optimize_for)
                if spur_path:
                    total_path = root_path[:-1] + spur_path
                    if total_path not in confirmed:
                        cost = self._path_cost(total_path, optimize_for)
                        candidates.append((cost, total_path))

            if not candidates:
                break

            candidates.sort(key=lambda x: x[0])
            _, best = candidates.pop(0)
            confirmed.append(best)

        # Enrich routes
        return self._enrich_routes(confirmed, optimize_for)

    def _path_cost(self, path: list[str], optimize_for: str) -> float:
        total = 0
        for i in range(len(path) - 1):
            edge = self._get_edge_data(path[i], path[i + 1])
            if edge:
                total += self._edge_weight(edge, optimize_for)
            else:
                total += 9999
        return total

    def _enrich_routes(self, paths: list[list[str]], optimize_for: str) -> list[dict[str, Any]]:
        enriched = []
        for rank, path in enumerate(paths):
            edges_data = []
            for i in range(len(path) - 1):
                edge = self._get_edge_data(path[i], path[i + 1])
                if edge:
                    edges_data.append(edge)

            if not edges_data:
                continue

            total_hours = sum(e["base_hours"] * e["delay_factor"] for e in edges_data)
            total_cost = sum(e["base_cost"] for e in edges_data)
            avg_reliability = sum(e["reliability"] for e in edges_data) / len(edges_data)
            modes_used = list(set(e["mode"] for e in edges_data))

            waypoints = []
            for port_id in path:
                node = self.nodes.get(port_id, {})
                waypoints.append({
                    "id": port_id,
                    "name": node.get("name", port_id),
                    "lat": node.get("lat", 0),
                    "lon": node.get("lon", 0),
                    "type": node.get("type", "unknown"),
                })

            tradeoff = self._generate_tradeoff(rank, total_hours, total_cost, avg_reliability)

            enriched.append({
                "rank": rank + 1,
                "route_name": f"Route {chr(65 + rank)}: {' → '.join(n.get('name', n.get('id', '?'))[:12] for n in waypoints[:4])}{'...' if len(waypoints) > 4 else ''}",
                "waypoints": waypoints,
                "modes": modes_used,
                "total_hours": round(total_hours, 1),
                "total_days": round(total_hours / 24, 1),
                "base_cost_usd": round(total_cost),
                "reliability_score": round(avg_reliability, 1),
                "is_multimodal": len(modes_used) > 1,
                "chokepoints": [p for p in path if "CANAL" in p or "STRAIT" in p or "CAPE" in p],
                "tradeoffs": tradeoff,
                "recommendation": rank == 0,
            })

        return enriched

    def _generate_tradeoff(self, rank: int, hours: float, cost: float, reliability: float) -> str:
        if rank == 0:
            return "Optimal balanced route — best combination of speed, cost, and reliability"
        elif rank == 1:
            return f"Alternative path — {round(hours / 24, 1)} days transit, ${cost:,.0f} cost, {reliability:.0f}% reliable"
        return f"Economy option — lower cost at ${cost:,.0f} but {round(hours / 24, 1)} days transit time"

    def get_network_geojson(self) -> dict[str, Any]:
        """Return the full port network as GeoJSON for map visualization."""
        features = []

        # Port nodes as points
        for port_id, node in self.nodes.items():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [node["lon"], node["lat"]]},
                "properties": {
                    "id": port_id,
                    "name": node["name"],
                    "type": node["type"],
                    "city": node.get("city"),
                    "country": node.get("country"),
                    "capacity_teu": node.get("capacity_teu"),
                    "congestion_score": node.get("congestion_score", 0),
                },
            })

        # Route edges as LineStrings
        for from_id, edges in self.adjacency.items():
            from_node = self.nodes.get(from_id)
            if not from_node:
                continue
            for edge in edges:
                to_node = self.nodes.get(edge["to"])
                if not to_node:
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [from_node["lon"], from_node["lat"]],
                            [to_node["lon"], to_node["lat"]],
                        ],
                    },
                    "properties": {
                        "from": from_id,
                        "to": edge["to"],
                        "mode": edge["mode"],
                        "distance_km": edge["distance_km"],
                        "transit_hours": edge["base_hours"],
                        "cost": edge["base_cost"],
                        "reliability": edge["reliability"],
                        "delay_factor": edge["delay_factor"],
                    },
                })

        return {"type": "FeatureCollection", "features": features}

    def get_chokepoints(self) -> list[dict[str, Any]]:
        chokepoint_ids = [pid for pid, n in self.nodes.items() if n["type"] == "chokepoint"]
        results = []
        for cid in chokepoint_ids:
            node = self.nodes[cid]
            # Count edges passing through
            edge_count = len(self.adjacency.get(cid, []))
            congestion = port_congestion_engine.get_port_congestion(cid)
            results.append({
                "id": cid,
                "name": node["name"],
                "lat": node["lat"],
                "lon": node["lon"],
                "status": congestion["status"],
                "congestion_score": congestion["congestion_score"],
                "connections": edge_count,
                "trend": congestion["trend"],
            })
        return results


# Module-level singleton
route_graph = RouteGraph()


async def get_route_alternatives(shipment: dict[str, Any], disruption: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Backwards-compatible function used by existing routes router."""
    return await gemini_service.generate_route_alternatives(shipment, disruption)
