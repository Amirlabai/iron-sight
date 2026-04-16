import json
import os
import time
import logging
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.distance import cdist
from src.utils.config import MIN_IRAN_THRESHOLD, MAX_IRAN_THRESHOLD
from src.utils.text_utils import standardize_name

logger = logging.getLogger("IronSightBackend")

class TrackingEngine:
    def __init__(self, data_manager, db_manager=None):
        self.dm = data_manager
        self.db = db_manager
        self.verified_history = []
        self.last_sync_time = 0
        
        self.origins = {
            "Gaza": [31.4167, 34.3333],
            "Lebanon": [33.8886, 35.8623],
            "Yemen": [15.3547, 44.2067],
            "Iran": [32.4279, 53.6880]
        }
        self.boundaries = {}
        self.calc_boundaries = {}
        self.origins["North Iran"] = self.origins["Iran"]
        
        # Strategic metadata
        self.strategic_depths = {
            "Gaza": 0.5,
            "Lebanon": 0.5,
            "Iran": 13.0,
            "North Iran": 13.0,
            "Yemen": 20.0
        }
        self.zoom_levels = {
            "Gaza": 8,
            "Lebanon": 7,
            "Iran": 6,
            "North Iran": 6,
            "Yemen": 6
        }
        
        self._load_borders()

    def _load_borders(self):
        """Initialize tactical and calculation boundaries from available geodata."""
        base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        try:
            geojson_path = os.path.join(base_dir, 'countries.geojson')
            if os.path.exists(geojson_path):
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geo_data = json.load(f)
                
                for feature in geo_data.get("features", []):
                    props = feature.get("properties", {})
                    loc_name = props.get("location", "").replace("Gaza Strip", "Gaza")
                    geom = feature.get("geometry", {})
                    if geom.get("type") == "Polygon":
                        raw_coords = geom.get("coordinates", [[]])[0]
                        flipped_coords = [[p[1], p[0]] for p in raw_coords]
                        self.boundaries[loc_name] = flipped_coords
                        if props.get("depth"): self.strategic_depths[loc_name] = float(props["depth"])
                        if props.get("zoom level"): self.zoom_levels[loc_name] = int(props["zoom level"])

                logger.info(f"TACTICAL_SILHOUETTES_LOADED: {len(self.boundaries)} regions.")
            else:
                borders_path = os.path.join(base_dir, 'tactical_borders.json')
                if os.path.exists(borders_path):
                    with open(borders_path, 'r') as f:
                        self.boundaries = json.load(f)
                    logger.info("LEGACY_TACTICAL_BOUNDARIES_LOADED")

            calc_path = os.path.join(base_dir, 'calculation_borders.json')
            if os.path.exists(calc_path):
                with open(calc_path, 'r') as f:
                    self.calc_boundaries = json.load(f)
                logger.info("STRATEGIC_CALCULATION_BORDERS_LOADED")
            else:
                self.calc_boundaries = self.boundaries.copy()
                logger.info("STRATEGIC_CALCULATION_FALLBACK: Using tactical boundaries.")
                
        except Exception as e:
            logger.warning(f"TACTICAL_BORDERS_LOAD_FAILURE: {e}. Using hardcoded fallbacks.")
            self.boundaries = {
                "Gaza": [[31.2, 34.2], [31.6, 34.6], [31.5, 34.6], [31.2, 34.3]],
                "Lebanon": [[33.1, 35.1], [33.5, 35.9], [34.7, 36.0], [34.7, 35.8]],
                "Yemen": [[12.6, 43.5], [16.6, 53.1], [19.0, 52.0], [17.5, 43.4]],
                "Iran": [[25.0, 61.0], [38.0, 63.0], [40.0, 44.0], [25.0, 55.0]],
                "North Iran": [[36.8, 53.8], [39.8, 43.8], [33.1, 46.2], [36.8, 53.8]]
            }
            self.calc_boundaries = self.boundaries.copy()

    def get_distance(self, c1, c2):
        return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)**0.5

    def get_convex_hull(self, points):
        pts = np.array(points)
        if len(pts) < 3: return pts.tolist() 
        try:
            hull = ConvexHull(pts)
            return pts[hull.vertices].tolist()
        except Exception:
            return pts.tolist() 

    def is_point_in_polygon(self, point, poly_name, use_tactical=False):
        boundaries = self.boundaries if use_tactical else self.calc_boundaries
        if poly_name not in boundaries: return False
        poly = np.array(boundaries[poly_name])
        return bool(self._ray_cast_vectorized(np.array([point]), poly)[0])

    @staticmethod
    def _ray_cast_vectorized(pts, poly):
        x, y = pts[:, 0], pts[:, 1]
        p1 = poly
        p2 = np.roll(poly, -1, axis=0)
        p1x, p1y = p1[:, 0], p1[:, 1]
        p2x, p2y = p2[:, 0], p2[:, 1]
        y_ = y[:, None]
        x_ = x[:, None]
        cond1 = y_ > np.minimum(p1y, p2y)
        cond2 = y_ <= np.maximum(p1y, p2y)
        cond3 = x_ <= np.maximum(p1x, p2x)
        nonzero_dy = p1y != p2y
        with np.errstate(divide='ignore', invalid='ignore'):
            xinters = np.where(nonzero_dy, (y_ - p1y) * (p2x - p1x) / np.where(nonzero_dy, p2y - p1y, 1.0) + p1x, np.inf)
        crossings = cond1 & cond2 & cond3 & ((p1x == p2x) | (x_ <= xinters))
        return crossings.sum(axis=1) % 2 == 1

    def calculate_regression_vector(self, cities):
        coords = list({tuple(c['coords']) for c in cities})
        if len(coords) < 2: return None
        pts = np.array(coords)
        cov = np.cov(pts.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        dominant = eigenvectors[:, np.argmax(eigenvalues)]
        return dominant.tolist()

    def cluster(self, cities, threshold_km=25.0):
        """Vectorized clustering using pre-computed distance matrix and connected components."""
        if not cities: return []
        
        # 1. Coordinate Matrix (N x 2)
        coords = np.array([c['coords'] for c in cities])
        
        # 2. Adjacency via Distance Matrix
        # Note: cdist uses Euclidean in deg. For tactical accuracy, we use threshold_km/111
        deg = threshold_km / 111.0
        dist_matrix = cdist(coords, coords)
        adj_matrix = dist_matrix <= deg
        
        # 3. Extract Components
        try:
            from scipy.sparse import csr_matrix
            from scipy.sparse.csgraph import connected_components
            n_components, labels = connected_components(csr_matrix(adj_matrix))
            
            # 4. Vectorized Grouping & Centroids
            clusters = []
            for i in range(n_components):
                mask = (labels == i)
                members = [cities[j] for j, m in enumerate(mask) if m]
                # Vectorized mean of members
                member_coords = coords[mask]
                centroid = np.mean(member_coords, axis=0).tolist()
                clusters.append({'centroid': centroid, 'cities': members})
            return clusters
            
        except ImportError:
            # Maintain legacy fallback if scipy.sparse is missing (unlikely in this env)
            parent = list(range(len(cities)))
            def find(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i
            def union(i, j):
                pi, pj = find(i), find(j)
                if pi != pj: parent[pi] = pj
            
            close = np.argwhere(dist_matrix <= deg)
            for i, j in close:
                if i < j: union(int(i), int(j))
            
            groups = {}
            for idx, city in enumerate(cities):
                root = find(idx)
                groups.setdefault(root, []).append(city)
            
            return [{'centroid': np.mean([m['coords'] for m in mem], axis=0).tolist(), 'cities': mem} for mem in groups.values()]

    async def _sync_verified_history(self):
        """Periodically refresh the local cache of verified historical clusters."""
        if not self.db: return
        now = time.time()
        if now - self.last_sync_time < 300: # Sync every 5 minutes
            return
        
        try:
            self.verified_history = await self.db.get_verified_history(limit=2000)
            self.last_sync_time = now
            if not self.verified_history:
                logger.warning("TACTICAL_ML_SYNC: Zero valid verified records loaded. Historical matching disabled.")
            else:
                logger.info(f"TACTICAL_ML_SYNC: {len(self.verified_history)} verified records loaded.")
        except Exception as e:
            logger.error(f"ML_SYNC_FAILURE: {e}")

    def _lookup_historical_match(self, cities):
        """
        KNN-lite: Matches the current city set against verified historical clusters.
        1. Exact City Set Hash
        2. Centroid Proximity (<5km)
        """
        if not self.verified_history: return None
        
        current_names = {c['name'] for c in cities if c.get('name')}
        current_centroid = np.mean([c['coords'] for c in cities], axis=0)
        
        best_match = None
        best_score = 0
        
        for item in self.verified_history:
            # Guard: skip records with empty or missing trajectories
            trajectories = item.get("trajectories")
            if not trajectories:
                continue

            hist_names = {c['name'] for c in item.get("all_cities", []) if c.get('name')}
            
            # Exact Match
            if current_names == hist_names:
                return trajectories[0]["origin"], trajectories[0].get("depth", 10.0)
            
            # Centroid Proximity
            hist_centroid = np.array(item.get("center") or [0, 0])
            dist = np.linalg.norm(current_centroid - hist_centroid) * 111.0 # approx degree to km
            
            if dist < 5.0: # Close enough to be the same geographic salvo
                intersection = current_names.intersection(hist_names)
                union = current_names.union(hist_names)
                jaccard = len(intersection) / len(union) if union else 0
                
                if jaccard > 0.8: # High similarity
                    org = trajectories[0]["origin"]
                    depth = trajectories[0].get("depth", 10.0)
                    return org.strip(), depth
        
        return None

    async def get_origin(self, cluster_cities, manual_origin=None):
        if manual_origin: return manual_origin.strip(), self.strategic_depths.get(manual_origin.strip(), 10.0)
        
        # 1. Historical Lookup (ML-lite)
        await self._sync_verified_history()
        hist_match = self._lookup_historical_match(cluster_cities)
        if hist_match:
            logger.info(f"TACTICAL_ML_HIT: Matched historical verified salvo -> {hist_match[0]}")
            return hist_match
        
        # 2. Traditional Vectorial Analysis
        coords = np.array([c['coords'] for c in cluster_cities])
        centroid = np.mean(coords, axis=0).tolist()
        vector = self.calculate_regression_vector(cluster_cities)
        if vector:
            v_lat, v_lon = vector
            mag = (v_lat**2 + v_lon**2)**0.5
            if mag == 0: v_lat, v_lon, mag = 0.5, 1.0, 1.118
            v_lat, v_lon = v_lat/mag, v_lon/mag
            # Orient away from target
            isr = [31.7, 35.2]
            dist_now = self.get_distance(centroid, isr)
            dist_next = self.get_distance([centroid[0] + v_lat*0.1, centroid[1] + v_lon*0.1], isr)
            if dist_next < dist_now and len(cluster_cities) <= MIN_IRAN_THRESHOLD:
                v_lat, v_lon = -v_lat, -v_lon
            # Vector Projections Strategy
            depth = 7
            proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
            for territory in ["North Iran", "Iran", "Yemen"]:
                if self.is_point_in_polygon(proj, territory):
                    return ("Iran", 16.0) if territory.endswith("Iran") else ("Yemen", depth)
            depth = 0.5
            proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
            for territory in ["Lebanon", "Gaza"]:
                if self.is_point_in_polygon(proj, territory): return territory.strip(), depth
        # Fallback Heuristics
        dist_gaza = self.get_distance(centroid, self.origins["Gaza"])
        dist_lebanon = self.get_distance(centroid, self.origins["Lebanon"])
        return ("Gaza", 0.5) if dist_gaza < dist_lebanon else ("Lebanon", 0.5)

    def get_projected_origin(self, cluster_cities, origin_name, depth=None):
        coords = np.array([c['coords'] for c in cluster_cities])
        _cnt = np.mean(coords, axis=0)
        cnt_lat, cnt_lon = float(_cnt[0]), float(_cnt[1])
        vector = self.calculate_regression_vector(cluster_cities)
        origin_center = self.origins.get(origin_name, [0, 0])
        if not vector: return origin_center
        v_lat, v_lon = vector
        mag = (v_lat**2 + v_lon**2)**0.5
        if mag == 0: return origin_center
        v_lat, v_lon = v_lat/mag, v_lon/mag
        # Orient away from target
        dist_current = self.get_distance([cnt_lat, cnt_lon], origin_center)
        dist_forward = self.get_distance([cnt_lat + v_lat*0.1, cnt_lon + v_lon*0.1], origin_center)
        if dist_forward > dist_current:
            if len(cluster_cities) <= MIN_IRAN_THRESHOLD or origin_name in ["Lebanon", "Gaza"]:
                v_lat, v_lon = -v_lat, -v_lon
        scalar = depth if depth is not None else self.strategic_depths.get(origin_name, 10.0)
        proj = [cnt_lat + v_lat * scalar, cnt_lon + v_lon * scalar]
        if not self.is_point_in_polygon(proj, origin_name, use_tactical=True):
            return self.origins.get(origin_name, proj)
        return proj
