import logging
from src.utils.config import MAX_IRAN_THRESHOLD
from src.utils.text_utils import standardize_name

logger = logging.getLogger("IronSightBackend")

class ThreatProcessor:
    def __init__(self, engine):
        self.engine = engine

    def process(self, alert_type, cities_raw):
        """Route threat analysis based on category and inject visual orchestration.
        No more DBSCAN clustering. All cities within a single alert ID form one unified cluster."""
        if alert_type == "missiles":
            return self._process_missiles(cities_raw)
        elif alert_type == "hostileAircraftIntrusion":
            return self._process_drone(cities_raw)
        elif alert_type == "terroristInfiltration":
            return self._process_infiltration(cities_raw)
        elif alert_type == "earthQuake":
            return self._process_earthquake(cities_raw)
        return None

    def _build_unified_cluster(self, city_coords):
        """Treat all cities as a single cluster: one hull, one centroid."""
        cnt = [sum(c['coords'][0] for c in city_coords) / len(city_coords), 
               sum(c['coords'][1] for c in city_coords) / len(city_coords)]
        hull = self.engine.get_convex_hull([c['coords'] for c in city_coords])
        return cnt, hull

    def _process_missiles(self, cities_raw):
        """Ballistic trajectory analysis. Single unified cluster per ID, no DBSCAN."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        cnt, hull = self._build_unified_cluster(city_coords)

        total_unique = len({c['name'] for c in city_coords})
        force_iran = total_unique > MAX_IRAN_THRESHOLD

        org_name, depth = self.engine.get_origin(city_coords)
        if force_iran:
            org_name, depth = "Iran", self.engine.strategic_depths["Iran"]

        border_entry = self.engine.get_projected_origin(city_coords, org_name, depth=depth)

        trajectories = [{
            "origin": org_name,
            "origin_coords": border_entry,
            "marker_coords": self.engine.origins[org_name],
            "target_coords": cnt
        }]

        processed_clusters = [{
            "origin": org_name,
            "centroid": cnt,
            "cities": city_coords,
            "hull": hull
        }]

        display_origin = "Iran" if org_name == "North Iran" else org_name
        title = f"{display_origin} Salvo"

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

    def _process_drone(self, cities_raw):
        """Hostile Aircraft: unified cluster for the flight path zone."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        cnt, hull = self._build_unified_cluster(city_coords)

        processed_clusters = [{
            "origin": "hostileAircraftIntrusion",
            "centroid": cnt,
            "cities": city_coords,
            "hull": hull
        }]

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

    def _process_infiltration(self, cities_raw):
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

    def _process_earthquake(self, cities_raw):
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

    def _map_cities(self, cities_raw):
        mapped = []
        for c in cities_raw:
            std = standardize_name(c)
            if std in self.engine.dm.city_map:
                mapped.append({
                    "name": c, 
                    "coords": [self.engine.dm.city_map[std]['lat'], self.engine.dm.city_map[std]['lon']]
                })
        return mapped
