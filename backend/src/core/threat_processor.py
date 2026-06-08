import logging
import numpy as np
from src.utils.config import MAX_IRAN_THRESHOLD, MISSILE_INFLATION_FACTOR, DRONE_INFLATION_FACTOR, DEFAULT_INFLATION_FACTOR
from src.utils.text_utils import standardize_name
from src.core.missile_origins import build_missile_origins

logger = logging.getLogger("IronSightBackend")

class ThreatProcessor:
    def __init__(self, engine):
        self.engine = engine

    async def process(
        self,
        alert_type,
        cities_raw,
        active_events=None,
        has_newsflash_in_batch=False,
        use_polygon_hulls=False,
    ):
        """Route threat analysis based on category and inject visual orchestration."""
        if alert_type == "missiles":
            return await self._process_missiles(
                cities_raw, active_events, has_newsflash_in_batch, use_polygon_hulls
            )
        elif alert_type == "hostileAircraftIntrusion":
            return await self._process_drone(cities_raw, use_polygon_hulls)
        elif alert_type == "terroristInfiltration":
            return await self._process_infiltration(cities_raw, use_polygon_hulls)
        elif alert_type == "earthQuake":
            return await self._process_earthquake(cities_raw, use_polygon_hulls)
        elif alert_type == "newsFlash":
            return await self._process_news_flash(cities_raw, use_polygon_hulls)
        return None

    def _cluster_hull(self, city_coords, factor, use_polygon_hulls=False):
        coords = [c["coords"] for c in city_coords]
        hull_cities = city_coords if use_polygon_hulls else None
        return self.engine.get_inflated_hull(coords, factor, cities=hull_cities)

    def _centroid(self, city_coords):
        if not city_coords:
            return [0, 0]
        coords = np.array([c["coords"] for c in city_coords])
        return np.mean(coords, axis=0).tolist()

    def _build_unified_cluster(self, city_coords, factor=DEFAULT_INFLATION_FACTOR, use_polygon_hulls=False):
        """Treat all cities as a single cluster: one hull, one centroid."""
        if not city_coords:
            return [0, 0], []
        cnt = self._centroid(city_coords)
        hull = self._cluster_hull(city_coords, factor, use_polygon_hulls)
        return cnt, hull

    async def _process_missiles(
        self, cities_raw, active_events=None, has_newsflash_in_batch=False, use_polygon_hulls=False
    ):
        """Ballistic trajectory analysis. Single unified cluster per ID, no DBSCAN."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords:
            return None

        cnt = self._centroid(city_coords)
        allow_strategic = has_newsflash_in_batch
        total_unique = len({c["name"] for c in city_coords})
        force_iran = total_unique > MAX_IRAN_THRESHOLD and allow_strategic

        raw_clusters = self.engine.cluster(city_coords)
        origin_result = await build_missile_origins(
            self.engine,
            raw_clusters,
            city_coords,
            allow_strategic=allow_strategic,
            force_iran=force_iran,
            hull_for_cities=lambda cities: self._cluster_hull(
                cities, MISSILE_INFLATION_FACTOR, use_polygon_hulls
            ),
        )

        result = {
            "type": "alert",
            "category": "missiles",
            "title": origin_result["title"],
            "clusters": origin_result["clusters"],
            "trajectories": origin_result["trajectories"],
            "all_cities": city_coords,
            "center": cnt,
            "zoom_level": origin_result["zoom_level"],
            "visual_config": {
                "color": "#ff3b30",
                "pulse": "high",
                "movement": "linear"
            }
        }
        for key in ("origin_candidates", "origin_ml_scores", "origin_resolved_by", "origin_ml_confidence"):
            if origin_result.get(key) is not None:
                result[key] = origin_result[key]
        return result

    async def _process_drone(self, cities_raw, use_polygon_hulls=False):
        """Hostile Aircraft: unified cluster for the flight path zone."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords:
            return None

        cnt, _ = self._build_unified_cluster(
            city_coords, DRONE_INFLATION_FACTOR, use_polygon_hulls
        )

        raw_clusters = self.engine.cluster(city_coords)
        processed_clusters = []
        for rc in raw_clusters:
            processed_clusters.append({
                "origin": "hostileAircraftIntrusion",
                "centroid": rc['centroid'],
                "cities": rc['cities'],
                "hull": self._cluster_hull(rc["cities"], DRONE_INFLATION_FACTOR, use_polygon_hulls),
            })

        return {
            "type": "alert",
            "category": "hostileAircraftIntrusion",
            "title": "Hostile Aircraft Intrusion",
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": cnt,
            "zoom_level": 10,
            "visual_config": {
                "color": "#ff9500",
                "pulse": "medium",
                "movement": "circular_sweep",
                "icon": "orange_arrow_tail"
            }
        }

    def _process_per_city_markers(self, city_coords, origin, title, zoom_level, visual_config, use_polygon_hulls=False):
        processed_clusters = []
        for city in city_coords:
            processed_clusters.append({
                "origin": origin,
                "centroid": city["coords"],
                "cities": [city],
                "hull": self._cluster_hull([city], 1.0, use_polygon_hulls),
            })
        center = city_coords[0]["coords"] if city_coords else [31.7, 35.2]
        return {
            "type": "alert",
            "category": origin,
            "title": title,
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": center,
            "zoom_level": zoom_level,
            "visual_config": visual_config,
        }

    async def _process_infiltration(self, cities_raw, use_polygon_hulls=False):
        city_coords = self._map_cities(cities_raw)
        if not city_coords:
            return None
        return self._process_per_city_markers(
            city_coords,
            "terroristInfiltration",
            "Terrorist Infiltration",
            11,
            {
                "color": "#b518ff",
                "pulse": "ripple",
                "movement": "converge",
                "icon": "purple_dots",
            },
            use_polygon_hulls,
        )

    async def _process_earthquake(self, cities_raw, use_polygon_hulls=False):
        city_coords = self._map_cities(cities_raw)
        if not city_coords:
            return None
        return self._process_per_city_markers(
            city_coords,
            "earthQuake",
            "Earthquake Alert",
            9,
            {
                "color": "#4cd964",
                "pulse": "slow_steady",
                "movement": "static",
            },
            use_polygon_hulls,
        )

    async def _process_news_flash(self, cities_raw, use_polygon_hulls=False):
        """News Flash: originless tactical polygons for potential threat warnings."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords:
            return None

        cnt, hull = self._build_unified_cluster(city_coords, use_polygon_hulls=use_polygon_hulls)

        processed_clusters = [{
            "origin": "newsFlash",
            "centroid": cnt,
            "cities": city_coords,
            "hull": hull
        }]

        return {
            "type": "alert",
            "category": "newsFlash",
            "title": "Potential Threat Warning",
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": cnt,
            "zoom_level": 8,
            "visual_config": {
                "color": "#f8f8f8",
                "pulse": "slow_steady",
                "movement": "static",
                "opacity": 0.4
            }
        }

    def _map_cities(self, cities_raw):
        mapped = []
        for c in cities_raw:
            std = standardize_name(c)
            if std in self.engine.dm.city_map:
                city_entry = self.engine.dm.city_map[std]
                city_id = self.engine.dm.city_to_id.get(std)
                city_boundary = self.engine.city_polygons.get(str(city_id)) if city_id is not None else None
                mapped.append({
                    "name": city_entry.get("name") or c,
                    "coords": [city_entry['lat'], city_entry['lon']],
                    "area": city_entry.get('area', 'Other'),
                    "city_id": city_id,
                    "boundary": city_boundary
                })
        return mapped
