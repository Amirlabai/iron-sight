import logging
from src.utils.config import MAX_IRAN_THRESHOLD
from src.utils.text_utils import standardize_name

logger = logging.getLogger("IronSightBackend")

class ThreatProcessor:
    def __init__(self, engine):
        self.engine = engine

    def process(self, alert_type, cities_raw):
        """Route threat analysis based on category and inject visual orchestration."""
        if alert_type == "missiles":
            return self._process_missiles(cities_raw)
        elif alert_type == "hostileAircraftIntrusion":
            return self._process_drone(cities_raw)
        elif alert_type == "terroristInfiltration":
            return self._process_infiltration(cities_raw)
        elif alert_type == "earthQuake":
            return self._process_earthquake(cities_raw)
        return None

    def _process_missiles(self, cities_raw):
        """Standard ballistic trajectory and clustering analysis."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None

        total_unique = len({c['name'] for c in city_coords})
        force_iran = total_unique > MAX_IRAN_THRESHOLD
        raw_clusters = self.engine.cluster(city_coords)
        
        origin_groups = {}
        for cl in raw_clusters:
            org_name, depth = self.engine.get_origin(cl['cities'])
            if force_iran: org_name, depth = "Iran", self.engine.strategic_depths["Iran"]
            
            if org_name not in origin_groups:
                origin_groups[org_name] = {"cities": [], "depth": depth}
            
            for city in cl['cities']:
                if city['name'] not in {c['name'] for c in origin_groups[org_name]["cities"]}:
                    origin_groups[org_name]["cities"].append(city)

        processed_clusters = []
        trajectories = []
        for org_name, group in origin_groups.items():
            cities = group["cities"]
            cnt = [sum(c['coords'][0] for c in cities) / len(cities), 
                   sum(c['coords'][1] for c in cities) / len(cities)]
            border_entry = self.engine.get_projected_origin(cities, org_name, depth=group["depth"])
            trajectories.append({
                "origin": org_name,
                "origin_coords": border_entry,
                "marker_coords": self.engine.origins[org_name],
                "target_coords": cnt
            })
            processed_clusters.append({
                "origin": org_name, "centroid": cnt, "cities": cities, 
                "hull": self.engine.get_convex_hull([c['coords'] for c in cities])
            })

        display_origins = [("Iran" if o == "North Iran" else o) for o in origin_groups.keys()]
        title = f"{' & '.join(set(display_origins))} Salvo"

        return {
            "type": "alert",
            "category": "missiles",
            "title": title,
            "clusters": processed_clusters,
            "trajectories": trajectories,
            "all_cities": city_coords,
            "visual_config": {
                "color": "#ff3b30", # Rocket Red
                "pulse": "high",
                "movement": "linear"
            }
        }

    def _process_drone(self, cities_raw):
        """Hostile Aircraft: Orange arrows circulating target zones."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None
        
        # Drone uses standard clustering to figure out the flight path zone
        raw_clusters = self.engine.cluster(city_coords)
        processed_clusters = []
        for cl in raw_clusters:
            cities = cl['cities']
            cnt = [sum(c['coords'][0] for c in cities) / len(cities), 
                   sum(c['coords'][1] for c in cities) / len(cities)]
            processed_clusters.append({
                "origin": "hostileAircraftIntrusion",
                "centroid": cnt,
                "cities": cities,
                "hull": self.engine.get_convex_hull([c['coords'] for c in cities])
            })
            
        center = processed_clusters[0]["centroid"] if processed_clusters else [31.7, 35.2]

        return {
            "type": "alert",
            "category": "hostileAircraftIntrusion",
            "title": "Hostile Aircraft Intrusion",
            "clusters": processed_clusters,
            "trajectories": [],
            "all_cities": city_coords,
            "center": center,
            "zoom_level": 10,
            "visual_config": {
                "color": "#ff9500", # Tactical Orange
                "pulse": "medium",
                "movement": "circular_sweep",
                "icon": "orange_arrow_tail"
            }
        }

    def _process_infiltration(self, cities_raw):
        """Terrorist Infiltration: Deep green dots closing in on cities."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None
        
        # Infiltration is handled per-city (no clustering)
        processed_clusters = []
        for city in city_coords:
            processed_clusters.append({
                 "origin": "terroristInfiltration",
                 "centroid": city['coords'],
                 "cities": [city],
                 "hull": [city['coords']] # Single point hull
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
                "color": "#b518ff", # Tactical Purple
                "pulse": "ripple",
                "movement": "converge",
                "icon": "purple_dots"
            }
        }

    def _process_earthquake(self, cities_raw):
        """Seismic Event: Static green pulsing alerts."""
        city_coords = self._map_cities(cities_raw)
        if not city_coords: return None
        
        # Earthquakes are handled per-city
        processed_clusters = []
        for city in city_coords:
            processed_clusters.append({
                 "origin": "earthQuake",
                 "centroid": city['coords'],
                 "cities": [city],
                 "hull": [city['coords']] # Single point hull
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
                "color": "#4cd964", # Safety Green
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
