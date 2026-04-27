import logging
import numpy as np
from src.utils.config import MAX_IRAN_THRESHOLD, MISSILE_INFLATION_FACTOR, DRONE_INFLATION_FACTOR, DEFAULT_INFLATION_FACTOR
from src.utils.text_utils import standardize_name

logger = logging.getLogger("IronSightBackend")

class ThreatProcessor:
    def __init__(self, engine):
        self.engine = engine

    async def process(self, alert_type, cities_raw, active_events=None, has_newsflash_in_batch=False):
        """Route threat analysis based on category and inject visual orchestration.
        No more DBSCAN clustering. All cities within a single alert ID form one unified cluster."""
        if alert_type == "missiles":
            return await self._process_missiles(cities_raw, active_events, has_newsflash_in_batch)
        elif alert_type == "hostileAircraftIntrusion":
            return await self._process_drone(cities_raw)
        elif alert_type == "terroristInfiltration":
            return await self._process_infiltration(cities_raw)
        elif alert_type == "earthQuake":
            return await self._process_earthquake(cities_raw)
        elif alert_type == "newsFlash":
            return await self._process_news_flash(cities_raw)
        return None

    def _build_unified_cluster(self, city_coords, factor=DEFAULT_INFLATION_FACTOR):
        """Treat all cities as a single cluster: one hull, one centroid."""
        if not city_coords: return [0, 0], []
        coords = np.array([c['coords'] for c in city_coords])
        cnt = np.mean(coords, axis=0).tolist()
        hull = self.engine.get_inflated_hull(coords, factor)
        return cnt, hull

    async def _process_missiles(self, cities_raw, active_events=None, has_newsflash_in_batch=False):
        """Ballistic trajectory analysis. Single unified cluster per ID, no DBSCAN."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        cnt, hull = self._build_unified_cluster(city_coords, MISSILE_INFLATION_FACTOR)

        # Strategic origin gate: Iran/Yemen only valid when newsFlash context is present
        allow_strategic = has_newsflash_in_batch
        if not allow_strategic and active_events:
            allow_strategic = any(
                ev.get("category") == "newsFlash" and ev.get("end_time") is None
                for ev in active_events.values()
            )

        total_unique = len({c['name'] for c in city_coords})
        force_iran = total_unique > MAX_IRAN_THRESHOLD and allow_strategic

        raw_clusters = self.engine.cluster(city_coords)
        processed_clusters = []
        origin_groups = {}
        
        for rc in raw_clusters:
            raw_org, cl_depth = await self.engine.get_origin(rc['cities'], allow_strategic=allow_strategic)
            cl_org = raw_org.strip()
            if force_iran:
                cl_org, cl_depth = "Iran", self.engine.strategic_depths["Iran"]
                
            processed_clusters.append({
                "origin": cl_org,
                "centroid": rc['centroid'],
                "cities": rc['cities'],
                "hull": self.engine.get_inflated_hull([c['coords'] for c in rc['cities']], MISSILE_INFLATION_FACTOR)
            })
            if cl_org not in origin_groups:
                origin_groups[cl_org] = {"cities": [], "depth": cl_depth}
            origin_groups[cl_org]["cities"].extend(rc['cities'])
            # Standardize depth: Use the deepest calculated trajectory if multiple exist for same origin
            origin_groups[cl_org]["depth"] = max(origin_groups[cl_org]["depth"], cl_depth)
            
        trajectories = []
        for org, group_data in origin_groups.items():
            g_cities = group_data["cities"]
            g_depth = group_data["depth"]
            # Unified target center for this origin
            g_coords = np.array([c['coords'] for c in g_cities])
            g_cnt = np.mean(g_coords, axis=0).tolist()
            
            # Global origin projection for the entire front
            border_entry = self.engine.get_projected_origin(g_cities, org, depth=g_depth)
            
            trajectories.append({
                "origin": org,
                "origin_coords": border_entry,
                "marker_coords": self.engine.origins.get(org, border_entry),
                "target_coords": g_cnt,
                "depth": g_depth
            })

        if len(origin_groups) == 1:
            org_name = list(origin_groups.keys())[0]
            display_origin = "Iran" if org_name == "North Iran" else org_name
            title = f"{display_origin} Salvo"
        else:
            title = "Combined Salvo"

        return {
            "type": "alert",
            "category": "missiles",
            "title": title,
            "clusters": processed_clusters,
            "trajectories": trajectories,
            "all_cities": city_coords,
            "center": cnt,
            "visual_config": {
                "color": "#ff3b30",  # Rocket Red
                "pulse": "high",
                "movement": "linear"
            }
        }

    async def _process_drone(self, cities_raw):
        """Hostile Aircraft: unified cluster for the flight path zone."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        cnt, hull = self._build_unified_cluster(city_coords, DRONE_INFLATION_FACTOR)

        raw_clusters = self.engine.cluster(city_coords)
        processed_clusters = []
        for rc in raw_clusters:
            processed_clusters.append({
                "origin": "hostileAircraftIntrusion",
                "centroid": rc['centroid'],
                "cities": rc['cities'],
                "hull": self.engine.get_inflated_hull([c['coords'] for c in rc['cities']], DRONE_INFLATION_FACTOR)
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
                "color": "#ff9500",  # Tactical Orange
                "pulse": "medium",
                "movement": "circular_sweep",
                "icon": "orange_arrow_tail"
            }
        }

    async def _process_infiltration(self, cities_raw):
        """Terrorist Infiltration: per-city markers within a unified group."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        # Infiltration keeps per-city markers for tactical precision
        processed_clusters = []
        for city in city_coords:
            processed_clusters.append({
                 "origin": "terroristInfiltration",
                 "centroid": city['coords'],
                 "cities": [city],
                 "hull": [city['coords']]
            })

        center = city_coords[0]['coords'] if city_coords else [31.7, 35.2]
            
        return {
            "type": "alert",
            "category": "terroristInfiltration",
            "title": "Terrorist Infiltration",
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": center,
            "zoom_level": 11,
            "visual_config": {
                "color": "#b518ff",  # Tactical Purple
                "pulse": "ripple",
                "movement": "converge",
                "icon": "purple_dots"
            }
        }

    async def _process_earthquake(self, cities_raw):
        """Seismic Event: per-city static pulsing alerts."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None
        
        # Earthquakes are handled per-city
        processed_clusters = []
        for city in city_coords:
            processed_clusters.append({
                 "origin": "earthQuake",
                 "centroid": city['coords'],
                 "cities": [city],
                 "hull": [city['coords']]
            })
            
        center = city_coords[0]['coords'] if city_coords else [31.7, 35.2]

        return {
            "type": "alert",
            "category": "earthQuake",
            "title": "Earthquake Alert",
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": center,
            "zoom_level": 9,
            "visual_config": {
                "color": "#4cd964",  # Safety Green
                "pulse": "slow_steady",
                "movement": "static"
            }
        }

    async def _process_news_flash(self, cities_raw):
        """News Flash: originless tactical polygons for potential threat warnings."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        cnt, hull = self._build_unified_cluster(city_coords)

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
                "color": "#f8f8f8",  # Ghost White
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
                mapped.append({
                    "name": c, 
                    "coords": [self.engine.dm.city_map[std]['lat'], self.engine.dm.city_map[std]['lon']],
                    "area": self.engine.dm.city_map[std].get('area', 'Other')
                })
        return mapped
