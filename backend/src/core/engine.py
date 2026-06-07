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
        # Ray march along regression vector (degrees)
        self.ray_step = 0.1
        self.entry_inset = 0.1
        self.display_inset = 0.1
        self.tactical_display_max_depth = {
            "Gaza": 3.0,
            "Lebanon": 4.0,
            "Iran": 42.0,
            "North Iran": 42.0,
            "Yemen": 50.0,
        }
        
        self.city_polygons = {}
        self._load_borders()

    @property
    def regional_entry_inset(self):
        return self.entry_inset

    @regional_entry_inset.setter
    def regional_entry_inset(self, value):
        self.entry_inset = value

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
                        raw_rings = geom.get("coordinates", [])
                        flipped_rings = [
                            [[p[1], p[0]] for p in ring] for ring in raw_rings
                        ]
                        self.boundaries[loc_name] = (
                            flipped_rings[0] if len(flipped_rings) == 1 else flipped_rings
                        )
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
                
            from src.utils.config import POLYGONS_DATA_FILE
            if os.path.exists(POLYGONS_DATA_FILE):
                with open(POLYGONS_DATA_FILE, 'r') as f:
                    self.city_polygons = json.load(f)
                logger.info(f"CITY_POLYGONS_LOADED: {len(self.city_polygons)} outlines.")
                
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

    def get_inflated_hull(self, points, factor=1.0, cities=None):
        """Compute convex hull and inflate vertices outward from centroid by the given factor.
        If cities are provided, uses their high-fidelity polygons if available."""
        all_pts = []
        if cities:
            for city in cities:
                std = standardize_name(city.get('name'))
                city_id = self.dm.city_to_id.get(std)
                poly = self.city_polygons.get(str(city_id))
                if poly:
                    all_pts.extend(poly)
                else:
                    all_pts.append(city.get('coords'))
        else:
            all_pts = points

        pts = np.array(all_pts)
        
        if len(pts) == 1:
            # Single point fallback: Tactical diamond
            p = pts[0]
            offset = 0.015 * factor  # Scaled by inflation
            hull = [
                [p[0] + offset, p[1]],
                [p[0], p[1] + offset],
                [p[0] - offset, p[1]],
                [p[0], p[1] - offset]
            ]
            return hull
            
        if len(pts) < 3:
            # 2 points or sparse set: Inflate away from centroid
            cnt = np.mean(pts, axis=0)
            hull = cnt + (pts - cnt) * factor
            return hull.tolist()

        try:
            ch = ConvexHull(pts)
            hull_pts = pts[ch.vertices]
            cnt = np.mean(hull_pts, axis=0)
            inflated = cnt + (hull_pts - cnt) * factor
            return inflated.tolist()
        except Exception:
            return pts.tolist()

    @staticmethod
    def _boundary_is_multi_ring(boundary):
        if not boundary:
            return False
        first = boundary[0]
        return (
            isinstance(first, (list, tuple))
            and len(first) > 0
            and isinstance(first[0], (list, tuple, np.ndarray))
        )

    def is_point_in_polygon(self, point, poly_name, use_tactical=False):
        boundaries = self.boundaries if use_tactical else self.calc_boundaries
        if poly_name not in boundaries:
            return False
        boundary = boundaries[poly_name]
        if self._boundary_is_multi_ring(boundary):
            outer = np.array(boundary[0])
            if not bool(self._ray_cast_vectorized(np.array([point]), outer)[0]):
                return False
            for hole in boundary[1:]:
                if bool(self._ray_cast_vectorized(np.array([point]), np.array(hole))[0]):
                    return False
            return True
        poly = np.array(boundary)
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

    def _cluster_centroid(self, cluster_cities):
        coords = np.array([c['coords'] for c in cluster_cities])
        return np.mean(coords, axis=0).tolist()

    def _normalize_regression_vector(self, vector):
        v_lat, v_lon = vector
        mag = (v_lat ** 2 + v_lon ** 2) ** 0.5
        if mag == 0:
            v_lat, v_lon, mag = 0.5, 1.0, 1.118
        return v_lat / mag, v_lon / mag

    def _orient_vector_away_from(self, centroid, v_lat, v_lon, reference, city_count):
        dist_now = self.get_distance(centroid, reference)
        dist_next = self.get_distance(
            [centroid[0] + v_lat * 0.1, centroid[1] + v_lon * 0.1], reference
        )
        flipped = dist_next < dist_now and city_count <= MIN_IRAN_THRESHOLD
        if flipped:
            v_lat, v_lon = -v_lat, -v_lon
        return v_lat, v_lon, flipped

    def _project_point(self, centroid, v_lat, v_lon, depth):
        return [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]

    def _match_territory_at_projection(self, centroid, v_lat, v_lon, depth, territories):
        proj = self._project_point(centroid, v_lat, v_lon, depth)
        for territory in territories:
            if self.is_point_in_polygon(proj, territory):
                return territory.strip(), proj
        return None, proj

    def _calc_polygon_names(self, origin_name):
        """Calc-border polygon keys for a locked origin label."""
        if origin_name in ("Iran", "North Iran"):
            return ["Iran", "North Iran"]
        return [origin_name]

    def _projection_max_depth(self, origin_name, depth):
        """Upper bound for calc ray-march along the regression line."""
        scalar = depth if depth is not None else self.strategic_depths.get(origin_name, 10.0)
        if origin_name in ("Gaza", "Lebanon"):
            return max(scalar, 0.5)
        if origin_name in ("Iran", "North Iran"):
            return max(scalar, 16.0)
        if origin_name == "Yemen":
            return max(scalar, self.strategic_depths.get("Yemen", 20.0))
        return scalar

    def _point_in_calc_origin(self, pt, origin_name):
        for pname in self._calc_polygon_names(origin_name):
            if pname in self.calc_boundaries and self.is_point_in_polygon(
                pt, pname, use_tactical=False
            ):
                return True
        return False

    def _depth_grid(self, min_d, max_d):
        min_d = float(min_d)
        max_d = float(max_d)
        if max_d <= min_d:
            return np.array([max_d])
        step = self.ray_step
        return np.arange(min_d, max_d + step / 2, step)

    def _points_on_ray(self, centroid, v_lat, v_lon, depths):
        depths = np.asarray(depths, dtype=float)
        c = np.asarray(centroid, dtype=float)
        direction = np.array([v_lat, v_lon], dtype=float)
        return c + depths[:, np.newaxis] * direction

    def _points_in_boundary(self, pts, boundary):
        if self._boundary_is_multi_ring(boundary):
            outer = np.array(boundary[0])
            inside = self._ray_cast_vectorized(pts, outer)
            for hole in boundary[1:]:
                inside &= ~self._ray_cast_vectorized(pts, np.array(hole))
            return inside
        poly = np.array(boundary)
        return self._ray_cast_vectorized(pts, poly)

    def _points_in_calc_boundary(self, pts, boundary):
        return self._points_in_boundary(pts, boundary)

    def _tactical_polygon_name(self, origin_name):
        if origin_name == "North Iran":
            return "Iran"
        return origin_name

    def _tactical_inside_mask(self, pts, tactical_name):
        if len(pts) == 0:
            return np.zeros(0, dtype=bool)
        boundary = self.boundaries.get(tactical_name)
        if not boundary:
            return np.zeros(len(pts), dtype=bool)
        return self._points_in_boundary(pts, boundary)

    def _tactical_fallback_pin(self, tactical_name):
        boundary = self.boundaries.get(tactical_name)
        if boundary:
            outer = boundary[0] if self._boundary_is_multi_ring(boundary) else boundary
            ring = np.array(outer)
            if len(ring) > 0:
                return np.mean(ring, axis=0).tolist()
        fallback = self.origins.get(tactical_name)
        if fallback is not None:
            return list(fallback)
        return list(self.origins.get("Iran", [0, 0]))

    def _deepest_inside_after_entry(self, entry_i, depths, inside_mask, inset_amount, cap_depth):
        if inset_amount <= 0:
            return int(entry_i)
        entry_d = float(depths[entry_i])
        inset_max_d = min(entry_d + float(inset_amount), float(cap_depth))
        in_window = (
            (depths >= entry_d - 1e-9)
            & (depths <= inset_max_d + 1e-9)
            & inside_mask
        )
        valid = np.flatnonzero(in_window)
        if valid.size == 0:
            return int(entry_i)
        return int(valid[-1])

    def _calc_origin_inside_mask(self, pts, origin_name):
        if len(pts) == 0:
            return np.zeros(0, dtype=bool)
        mask = np.zeros(len(pts), dtype=bool)
        for pname in self._calc_polygon_names(origin_name):
            boundary = self.calc_boundaries.get(pname)
            if not boundary:
                continue
            mask |= self._points_in_calc_boundary(pts, boundary)
        return mask

    def _ray_march_calc_entry(self, centroid, v_lat, v_lon, origin_name, max_depth):
        """Calc-border entry (detection / replay). Deepest point within inset after first crossing."""
        min_depth = 0.05
        max_depth = float(max_depth)
        depths = self._depth_grid(min_depth, max_depth)
        pts = self._points_on_ray(centroid, v_lat, v_lon, depths)
        inside = self._calc_origin_inside_mask(pts, origin_name)
        hits = np.flatnonzero(inside)
        if hits.size == 0:
            return None, None

        entry_i = int(hits[0])
        best_i = self._deepest_inside_after_entry(
            entry_i, depths, inside, self.entry_inset, max_depth
        )
        return pts[best_i].tolist(), float(depths[best_i])

    def _ray_march_display_pin(self, centroid, v_lat, v_lon, origin_name, depth):
        """Calc entry for detection/replay; display = first tactical crossing + display_inset."""
        calc_max = self._projection_max_depth(origin_name, depth)
        tac_max = self.tactical_display_max_depth.get(origin_name, calc_max)
        grid_max = max(calc_max, tac_max)
        min_depth = 0.05

        depths = self._depth_grid(min_depth, grid_max)
        pts = self._points_on_ray(centroid, v_lat, v_lon, depths)
        calc_inside = self._calc_origin_inside_mask(pts, origin_name)
        tac_name = self._tactical_polygon_name(origin_name)
        tac_inside = self._tactical_inside_mask(pts, tac_name)

        calc_hits = np.flatnonzero(calc_inside)
        if calc_hits.size == 0:
            return None, None, None

        calc_entry_i = self._deepest_inside_after_entry(
            int(calc_hits[0]), depths, calc_inside, self.entry_inset, calc_max
        )
        calc_entry = pts[calc_entry_i].tolist()

        tac_all = np.flatnonzero(tac_inside)
        if tac_all.size == 0:
            return None, None, calc_entry

        tac_after_calc = tac_all[tac_all >= calc_entry_i]
        if tac_after_calc.size == 0:
            return None, None, calc_entry
        tac_entry_i = int(tac_after_calc[0])
        display_i = self._deepest_inside_after_entry(
            tac_entry_i, depths, tac_inside, self.display_inset, tac_max
        )

        return (
            pts[display_i].tolist(),
            float(depths[display_i]),
            calc_entry,
        )

    def project_origin_display(self, cluster_cities, origin_name, depth=None):
        """Return (display_pin_coords, calc_entry_coords or None) for trajectory storage."""
        centroid = self._cluster_centroid(cluster_cities)
        tactical_name = self._tactical_polygon_name(origin_name)
        origin_center = self.origins.get(origin_name, self.origins.get(tactical_name, [0, 0]))
        oriented = self._oriented_regression_vector(cluster_cities, centroid)
        if oriented is None:
            fb = list(origin_center)
            return fb, None

        v_lat, v_lon = oriented
        display, _, calc_entry = self._ray_march_display_pin(
            centroid, v_lat, v_lon, origin_name, depth
        )
        if display:
            return display, calc_entry

        calc_max = self._projection_max_depth(origin_name, depth)
        tac_max = self.tactical_display_max_depth.get(origin_name, calc_max)
        on_ray = self._project_point(centroid, v_lat, v_lon, tac_max)
        if self.boundaries.get(tactical_name) and self.is_point_in_polygon(
            on_ray, tactical_name, use_tactical=True
        ):
            return on_ray, calc_entry
        if calc_entry:
            return self._tactical_fallback_pin(tactical_name), calc_entry
        return self._project_point(
            centroid, v_lat, v_lon, self._projection_max_depth(origin_name, depth)
        ), None

    def project_calc_entry(self, cluster_cities, origin_name, depth=None):
        """Calc-border entry for detection, history-fixer, and suggest-origin APIs."""
        centroid = self._cluster_centroid(cluster_cities)
        oriented = self._oriented_regression_vector(cluster_cities, centroid)
        if oriented is None:
            return None
        v_lat, v_lon = oriented
        calc_max = self._projection_max_depth(origin_name, depth)
        hit, _ = self._ray_march_calc_entry(
            centroid, v_lat, v_lon, origin_name, calc_max
        )
        return hit

    def _oriented_regression_vector(self, cluster_cities, centroid):
        """PCA vector normalized and oriented away from Israel (matches label step)."""
        vector = self.calculate_regression_vector(cluster_cities)
        if not vector:
            return None
        v_lat, v_lon = self._normalize_regression_vector(vector)
        isr = [31.7, 35.2]
        v_lat, v_lon, _ = self._orient_vector_away_from(
            centroid, v_lat, v_lon, isr, len(cluster_cities)
        )
        return v_lat, v_lon

    async def trace_cluster_origin(self, cluster_cities, allow_strategic=True):
        """Return step-by-step origin trace for a single cluster (replay / debug)."""
        await self._sync_verified_history()
        centroid = self._cluster_centroid(cluster_cities)
        isr = [31.7, 35.2]
        city_count = len(cluster_cities)

        hist_match = self._lookup_historical_match(cluster_cities)
        if hist_match:
            return {
                "method": "historical",
                "origin": hist_match[0],
                "depth": hist_match[1],
                "centroid": centroid,
                "hist_match": True,
                "vector": None,
                "vector_flipped": False,
                "regional_proj": None,
                "regional_hit": None,
                "strategic_proj": None,
                "strategic_hit": None,
                "strategic_skipped": False,
                "fallback": None,
            }

        vector = self.calculate_regression_vector(cluster_cities)
        if not vector:
            dist_gaza = self.get_distance(centroid, self.origins["Gaza"])
            dist_lebanon = self.get_distance(centroid, self.origins["Lebanon"])
            origin = "Gaza" if dist_gaza < dist_lebanon else "Lebanon"
            return {
                "method": "fallback",
                "origin": origin,
                "depth": 0.5,
                "centroid": centroid,
                "hist_match": False,
                "vector": None,
                "vector_flipped": False,
                "regional_proj": None,
                "regional_hit": None,
                "strategic_proj": None,
                "strategic_hit": None,
                "strategic_skipped": not allow_strategic,
                "fallback": {"dist_gaza": dist_gaza, "dist_lebanon": dist_lebanon},
            }

        raw_vector = vector[:]
        v_lat, v_lon = self._normalize_regression_vector(vector)
        v_lat, v_lon, flipped = self._orient_vector_away_from(
            centroid, v_lat, v_lon, isr, city_count
        )

        regional_hit, regional_proj = self._match_territory_at_projection(
            centroid, v_lat, v_lon, 0.5, ["Lebanon", "Gaza"]
        )
        if regional_hit:
            return {
                "method": "regional_projection",
                "origin": regional_hit,
                "depth": 0.5,
                "centroid": centroid,
                "hist_match": False,
                "vector": raw_vector,
                "vector_flipped": flipped,
                "regional_proj": regional_proj,
                "regional_hit": regional_hit,
                "strategic_proj": None,
                "strategic_hit": None,
                "strategic_skipped": not allow_strategic,
                "fallback": None,
            }

        strategic_hit, strategic_proj = None, None
        strategic_skipped = not allow_strategic
        if allow_strategic:
            strategic_hit, strategic_proj = self._match_territory_at_projection(
                centroid, v_lat, v_lon, 7, ["North Iran", "Iran", "Yemen"]
            )
            if strategic_hit:
                origin = "Iran" if strategic_hit.endswith("Iran") else "Yemen"
                depth = 16.0 if strategic_hit.endswith("Iran") else 7
                return {
                    "method": "strategic_projection",
                    "origin": origin,
                    "depth": depth,
                    "centroid": centroid,
                    "hist_match": False,
                    "vector": raw_vector,
                    "vector_flipped": flipped,
                    "regional_proj": regional_proj,
                    "regional_hit": None,
                    "strategic_proj": strategic_proj,
                    "strategic_hit": strategic_hit,
                    "strategic_skipped": False,
                    "fallback": None,
                }

        dist_gaza = self.get_distance(centroid, self.origins["Gaza"])
        dist_lebanon = self.get_distance(centroid, self.origins["Lebanon"])
        origin = "Gaza" if dist_gaza < dist_lebanon else "Lebanon"
        return {
            "method": "fallback",
            "origin": origin,
            "depth": 0.5,
            "centroid": centroid,
            "hist_match": False,
            "vector": raw_vector,
            "vector_flipped": flipped,
            "regional_proj": regional_proj,
            "regional_hit": None,
            "strategic_proj": strategic_proj,
            "strategic_hit": None,
            "strategic_skipped": strategic_skipped,
            "fallback": {"dist_gaza": dist_gaza, "dist_lebanon": dist_lebanon},
        }

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

    async def get_origin(self, cluster_cities, manual_origin=None, allow_strategic=True):
        if manual_origin: return manual_origin.strip(), self.strategic_depths.get(manual_origin.strip(), 10.0)
        
        # 1. Historical Lookup (ML-lite)
        await self._sync_verified_history()
        hist_match = self._lookup_historical_match(cluster_cities)
        if hist_match:
            logger.info(f"TACTICAL_ML_HIT: Matched historical verified salvo -> {hist_match[0]}")
            return hist_match
        
        # 2. Traditional Vectorial Analysis
        trace = await self.trace_cluster_origin(cluster_cities, allow_strategic=allow_strategic)
        return trace["origin"], trace["depth"]

    def get_projected_origin(self, cluster_cities, origin_name, depth=None):
        """Display pin only (tactical silhouette). For calc-border use project_calc_entry."""
        display, _ = self.project_origin_display(cluster_cities, origin_name, depth)
        return display
