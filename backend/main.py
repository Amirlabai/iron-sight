import aiohttp
from aiohttp import web
import asyncio
import json
import re
import os
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import aiohttp_cors
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.distance import cdist

# Load Secrets
load_dotenv()

# --- Configuration ---
POLL_INTERVAL = 10
MIN_IRAN_THRESHOLD = 10
MAX_IRAN_THRESHOLD = 40
WS_PORT = int(os.environ.get("PORT", 8080)) # Dynamic port for Deployment
TIMEZONE = ZoneInfo("Asia/Jerusalem")
LAMAS_DATA_URL = "https://raw.githubusercontent.com/idodov/RedAlert/refs/heads/main/apps/red_alerts_israel/lamas_data.json"
LOCAL_DATA_FILE = "lamas_data.json"
OREF_API_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"

# DB Config
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "iron_sight_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "salvo_history")

if not MONGO_URI:
    logging.warning("MONGO_URI not found in environment. Persistence disabled.")

MISSION_KEY = os.getenv("MISSION_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - filename: %(filename)s - line: %(lineno)d - %(levelname)s - %(message)s')
logger = logging.getLogger("IronSightBackend")

# Load Version Info
VERSION = "0.0.0"
try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'version.json'), 'r') as f:
        vdata = json.load(f)
        VERSION = vdata.get("version", "0.0.0")
    logger.info(f"IRON SIGHT TACTICAL ENGINE - INITIALIZED (v{VERSION})")
except Exception as e:
    logger.warning(f"Could not load version.json: {e}")

# --- Utilities ---
@lru_cache(maxsize=1000)
def standardize_name(name):
    if not name: return ""
    name = re.sub(r'[\-\,\(\)\s]+', '', name)
    return name.strip()

# --- WebSocket Manager ---
class WebSocketManager:
    def __init__(self, mongo_manager, engine, port=WS_PORT):
        self.port = port
        self.mm = mongo_manager
        self.engine = engine
        self.clients = set()
        self.app = web.Application()
        
        # --- CORS Configuration ---
        self.cors = aiohttp_cors.setup(self.app, defaults={
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            ) for origin in ALLOWED_ORIGINS
        })

        # Add Tactical Routes with CORS
        self.add_route("GET", "/ws", self.ws_handler)
        self.add_route("GET", "/", self.health_handler)
        self.add_route("POST", "/api/calibrate", self.calibrate_handler)
        self.add_route("GET", "/api/history", self.history_handler)
        self.add_route("GET", "/api/cities", self.cities_handler)
        self.add_route("POST", "/api/analyze", self.analyze_handler)
        
        self.runner = None
        self.active_salvo_data = None

    def add_route(self, method, path, handler):
        resource = self.app.router.add_resource(path)
        self.cors.add(resource.add_route(method, handler))

    async def health_handler(self, request):
        return web.json_response({
            "status": "OPERATIONAL",
            "version": VERSION,
            "engine": "IRON SIGHT TACTICAL",
            "timestamp": datetime.now(TIMEZONE).isoformat()
        })

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        logger.info(f"Client connected. Total: {len(self.clients)}")
        
        # Send current history from MongoDB on connect
        try:
            history = await self.mm.get_history(limit=50)
            await ws.send_str(json.dumps({
                "type": "history_sync", 
                "data": history,
                "version": VERSION
            }))
        except Exception as e:
            logger.error(f"Error fetching history for client: {e}")

        # Send current active salvo if one exists
        if self.active_salvo_data:
            try:
                await ws.send_str(json.dumps(self.active_salvo_data, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Error sending active salvo to client: {e}")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT and msg.data == 'close':
                    await ws.close()
        finally:
            self.clients.remove(ws)
            logger.info(f"Client disconnected. Total: {len(self.clients)}")
        return ws

    async def calibrate_handler(self, request):
        """Manually override a salvo's origin and re-calculate strategic parameters."""
        try:
            data = await request.json()
            salvo_id = data.get("id")
            new_origin = data.get("origin")
            
            # --- MISSION KEY VALIDATION ---
            if MISSION_KEY:
                provided_key = request.headers.get("X-Mission-Key")
                if provided_key != MISSION_KEY:
                    logger.warning(f"UNAUTHORIZED_ACCESS_ATTEMPT: Invalid Mission Key for Salvo {salvo_id}")
                    return web.json_response({"error": "Unauthorized: Invalid Mission Key"}, status=401)

            if not salvo_id or not new_origin:
                return web.json_response({"error": "Missing ID or Origin"}, status=400)
                
            # Get the salvo
            salvo = await self.mm.collection.find_one({"id": salvo_id})
            if not salvo:
                return web.json_response({"error": "Salvo not found"}, status=404)
                
            # Re-calculate with the new origin
            cluster = salvo.get("clusters", [{}])[0]
            cities = cluster.get("cities", [])
            mid_lat, mid_lon = cluster.get("centroid", [31.7, 35.2])
            
            # Force the new origin logic
            strategic_zoom = self.engine.zoom_levels.get(new_origin, 8)
            
            # Use TrackingEngine 
            origin_coords = self.engine.get_projected_origin(cities, new_origin)
            
            fixed_pin = self.engine.origins.get(new_origin, origin_coords)
            
            # Update the DB
            update_data = {
                "manual_origin": new_origin,
                "trajectories": [{
                    "origin": new_origin,
                    "origin_coords": origin_coords,
                    "target_coords": [mid_lat, mid_lon],
                    "marker_coords": fixed_pin
                }],
                "zoom_level": strategic_zoom*1.2,
                "center": [(origin_coords[0] + mid_lat)/2, (origin_coords[1] + mid_lon)/2]
            }
            
            await self.mm.collection.update_one({"id": salvo_id}, {"$set": update_data})
            return web.json_response({"status": "success", "new_origin": new_origin})
        except Exception as e:
            logger.error(f"CALIBRATION_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def history_handler(self, request):
        """Serve the latest mission archive for frontend synchronization."""
        try:
            history = await self.mm.get_history(limit=50)
            return web.json_response(history)
        except Exception as e:
            logger.error(f"HISTORY_API_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def cities_handler(self, request):
        """Return the hierarchical city list grouped by regions."""
        try:
            # We expose the regions from the engine's data manager
            return web.json_response(self.engine.dm.areas)
        except Exception as e:
            logger.error(f"CITIES_API_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def analyze_handler(self, request):
        """Process a list of cities and return the tactical analysis without broadcast."""
        try:
            data = await request.json()
            cities = data.get("cities", [])
            if not cities:
                return web.json_response({"error": "No cities provided"}, status=400)
                
            analysis = self.engine.analyze_threat(cities)
            if not analysis:
                return web.json_response({"error": "Could not map cities to coordinates"}, status=404)
                
            return web.json_response(analysis)
        except Exception as e:
            logger.error(f"ANALYZE_API_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def broadcast(self, data):
        if not self.clients: return
        message = json.dumps(data, ensure_ascii=False)
        tasks = [client.send_str(message) for client in self.clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"WebSocket server started on port {self.port}")

# --- Persistence Manager ---
class MongoManager:
    def __init__(self, uri, db_name, collection_name):
        self.client = AsyncIOMotorClient(uri) if uri else None
        self.db = self.client[db_name] if self.client is not None else None
        self.collection = self.db[collection_name] if self.client is not None else None

    async def save_salvo(self, salvo):
        if self.collection is None: return
        try:
            # Use update_one with upsert to avoid duplicates if same ID appears
            await self.collection.update_one(
                {"id": salvo["id"]},
                {"$set": salvo},
                upsert=True
            )
            logger.info(f"Salvo {salvo['id']} saved to MongoDB.")
        except Exception as e:
            logger.error(f"Failed to save salvo to MongoDB: {e}")

    async def get_history(self, limit=50):
        if self.collection is None: return []
        try:
            cursor = self.collection.find().sort("_id", -1).limit(limit)
            history = await cursor.to_list(length=limit)
            # Remove MongoDB _id for clean JSON serialization
            for item in history:
                item.pop("_id", None)
            return history
        except Exception as e:
            logger.error(f"Failed to fetch history from MongoDB: {e}")
            return []

# --- Data Manager ---
class LamasDataManager:
    def __init__(self):
        self.city_map = {}
        self.areas = {}

    async def load(self):
        data_path = os.path.join(os.path.dirname(__file__), LOCAL_DATA_FILE)
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        else:
            logger.info("Downloading city data...")
            async with aiohttp.ClientSession() as session:
                async with session.get(LAMAS_DATA_URL) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download city data: Status {resp.status}")
                    text = await resp.text()
                    text = text.lstrip('\ufeff').strip()
                    data = json.loads(text)
            with open(data_path, 'w', encoding='utf-8-sig') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        self.areas = data.get('areas', {})
        for area, cities in self.areas.items():
            for city, details in cities.items():
                std = standardize_name(city)
                self.city_map[std] = {
                    "lat": float(details.get("lat", 0)),
                    "lon": float(details.get("long", 0)),
                    "area": area,
                    "name": city
                }
        logger.info(f"Loaded {len(self.city_map)} cities.")

# --- Processing Logic ---
class TrackingEngine:
    def __init__(self, data_manager):
        self.dm = data_manager
        self.origins = {
            "Gaza": [31.4167, 34.3333],
            "Lebanon": [33.8886, 35.8623],
            "Yemen": [15.3547, 44.2067],
            "Iran": [32.4279, 53.6880]
        }
        self.boundaries = {}
        self.calc_boundaries = {}
        # Strategic Pin Aliasing (Always ensure strategic corridors are mapped for pinning)
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
            "Gaza": 10,
            "Lebanon": 8,
            "Iran": 6,
            "North Iran": 6,
            "Yemen": 6
        }
        
        try:
            # --- MISSION: GeoJSON Migration (Silhouettes) ---
            geojson_path = os.path.join(os.path.dirname(__file__), 'countries.geojson')
            if os.path.exists(geojson_path):
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geo_data = json.load(f)
                
                for feature in geo_data.get("features", []):
                    props = feature.get("properties", {})
                    loc_name = props.get("location", "").replace("Gaza Strip", "Gaza")
                    
                    # Flip coordinates [lon, lat] -> [lat, lon] for internal processing
                    geom = feature.get("geometry", {})
                    if geom.get("type") == "Polygon":
                        # Nested arrays: [ [ [lon, lat], ... ] ]
                        raw_coords = geom.get("coordinates", [[]])[0]
                        flipped_coords = [[p[1], p[0]] for p in raw_coords]
                        self.boundaries[loc_name] = flipped_coords
                        
                        # Load Strategic Metadata from GeoJSON
                        if props.get("depth"):
                            self.strategic_depths[loc_name] = float(props["depth"])
                        if props.get("zoom level"):
                            self.zoom_levels[loc_name] = int(props["zoom level"])

                logger.info(f"TACTICAL SILHOUETTES LOADED FROM GEOJSON ({len(self.boundaries)} regions)")
            else:
                # Fallback to legacy tactical_borders.json if GeoJSON missing
                borders_path = os.path.join(os.path.dirname(__file__), 'tactical_borders.json')
                if os.path.exists(borders_path):
                    with open(borders_path, 'r') as f:
                        self.boundaries = json.load(f)
                    logger.info("LEGACY TACTICAL BOUNDARIES LOADED")

            # --- MISSION: Strategic Calculation Borders (Logic Core) ---
            # Preserved as requested. These are decoupled from visual silhouettes.
            calc_path = os.path.join(os.path.dirname(__file__), 'calculation_borders.json')
            if os.path.exists(calc_path):
                with open(calc_path, 'r') as f:
                    self.calc_boundaries = json.load(f)
                logger.info("STRATEGIC CALCULATION BORDERS LOADED")
            else:
                self.calc_boundaries = self.boundaries.copy()
                logger.info("USING TACTICAL BOUNDARIES FOR CALCULATION (FALLBACK)")
                
        except Exception as e:
            logger.warning(f"Using fallback boundaries: {e}")
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
        """Drop-in replacement: scipy's Qhull (C) vs Python monotone chain."""
        pts = np.array(points)
        if len(pts) < 3:
            return points  # degenerate: just return as-is
        try:
            hull = ConvexHull(pts)
            return pts[hull.vertices].tolist()
        except Exception:
            return points  # collinear points, etc. — safe fallback

    def is_point_in_polygon(self, point, poly_name, use_tactical=False):
        """
        Vectorized ray-casting for a SINGLE point against a polygon.
        Same API as before. For bulk point testing, call is_points_in_polygon().
        """
        boundaries = self.boundaries if use_tactical else self.calc_boundaries
        if poly_name not in boundaries:
            return False
        poly = np.array(boundaries[poly_name])
        return bool(self._ray_cast_vectorized(np.array([point]), poly)[0])

    def is_point_in_tactical_polygon(self, point, poly_name):
        return self.is_point_in_polygon(point, poly_name, use_tactical=True)

    def is_points_in_polygon(self, points, poly_name, use_tactical=False):
        """
        BULK version: test N points at once. Returns bool array shape (N,).
        Use this in any loop that tests many points against the same polygon.
        """
        boundaries = self.boundaries if use_tactical else self.calc_boundaries
        if poly_name not in boundaries:
            return np.zeros(len(points), dtype=bool)
        poly = np.array(boundaries[poly_name])
        return self._ray_cast_vectorized(np.array(points), poly)

    @staticmethod
    def _ray_cast_vectorized(pts, poly):
        """
        Vectorized ray-casting for N points vs one polygon.
        pts:  (N, 2) float array  [lat, lon]
        poly: (M, 2) float array  [lat, lon]
        Returns: (N,) bool array
        """
        x, y   = pts[:, 0], pts[:, 1]          # (N,)
        p1     = poly                            # (M, 2)
        p2     = np.roll(poly, -1, axis=0)       # (M, 2) — next vertex

        p1x, p1y = p1[:, 0], p1[:, 1]           # (M,)
        p2x, p2y = p2[:, 0], p2[:, 1]           # (M,)

        # Broadcast: (N, M) comparisons
        y_   = y[:, None]                        # (N, 1)
        x_   = x[:, None]                        # (N, 1)

        cond1 = y_ > np.minimum(p1y, p2y)
        cond2 = y_ <= np.maximum(p1y, p2y)
        cond3 = x_ <= np.maximum(p1x, p2x)

        nonzero_dy = p1y != p2y
        # Safe division — zero-dy edges always miss
        with np.errstate(divide='ignore', invalid='ignore'):
            xinters = np.where(
                nonzero_dy,
                (y_ - p1y) * (p2x - p1x) / np.where(nonzero_dy, p2y - p1y, 1.0) + p1x,
                np.inf
            )

        cond4 = (p1x == p2x) | (x_ <= xinters)
        crossings = cond1 & cond2 & cond3 & cond4   # (N, M)
        return crossings.sum(axis=1) % 2 == 1        # (N,) bool

    def calculate_regression_vector(self, cities):
        """np.cov + np.linalg.eigh — single LAPACK call, numerically stable."""
        coords = list({tuple(c['coords']) for c in cities})
        if len(coords) < 2:
            return None
        pts = np.array(coords)           # (K, 2)
        cov = np.cov(pts.T)              # (2, 2)
        # eigh is faster + always real for symmetric matrices
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        dominant = eigenvectors[:, np.argmax(eigenvalues)]   # (2,)
        return dominant.tolist()         # [v_lat, v_lon]

    def cluster(self, cities, threshold_km=25.0):
        """
        Chain-link clustering with numpy cdist to replace the O(n²) Python loop.
        For 180 cities this is ~150× faster than the original.
        """
        if not cities:
            return []

        deg = threshold_km / 111.0
        coords = np.array([c['coords'] for c in cities])  # (N, 2)

        # Full pairwise distance matrix in one C call
        dist_matrix = cdist(coords, coords)                # (N, N)

        # Union-Find for chain-link labeling
        parent = list(range(len(cities)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]   # path compression
                i = parent[i]
            return i

        def union(i, j):
            pi, pj = find(i), find(j)
            if pi != pj:
                parent[pi] = pj

        # Any pair within threshold → same cluster
        close = np.argwhere(dist_matrix <= deg)
        for i, j in close:
            if i < j:
                union(int(i), int(j))

        # Group by root
        groups: dict[int, list] = {}
        for idx, city in enumerate(cities):
            root = find(idx)
            groups.setdefault(root, []).append(city)

        # Build cluster dicts with centroid
        clusters = []
        for members in groups.values():
            c = np.mean([m['coords'] for m in members], axis=0)
            clusters.append({'centroid': c.tolist(), 'cities': members})

        return clusters

    def get_origin(self, cluster_cities, manual_origin=None):
        """Detect the likely source territory based on trajectory regression vector."""
        if manual_origin:
            return manual_origin
            
        centroid = [
            sum(c['coords'][0] for c in cluster_cities) / len(cluster_cities),
            sum(c['coords'][1] for c in cluster_cities) / len(cluster_cities)
        ]

        vector = self.calculate_regression_vector(cluster_cities)
        
        # 1. Vector-Based Trajectory Priority
        if vector:
            v_lat, v_lon = vector
            mag = (v_lat**2 + v_lon**2)**0.5
            if mag == 0:
                # Strategic Default: Single-hit targets gain a North-East axis for origin detection
                v_lat, v_lon = 0.5, 1.0
                mag = (v_lat**2 + v_lon**2)**0.5
            
            v_lat, v_lon = v_lat/mag, v_lon/mag
            
            # CONSISTENT ORIENTATION: Point AWAY from target (Israel) to trace origin
            isr = [31.7, 35.2]
            dist_now = self.get_distance(centroid, isr)
            dist_next = self.get_distance([centroid[0] + v_lat*0.1, centroid[1] + v_lon*0.1], isr)
            if dist_next < dist_now and len(cluster_cities) <= MIN_IRAN_THRESHOLD:
                v_lat, v_lon = -v_lat, -v_lon

            # Priority 1: Long-Range (Deep Projections Scan for strategic depth)
            # We scan multiple depths to hit different Iranian/Regional polygons
            depth = 7
            proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
            for territory in ["North Iran", "Iran", "Yemen"]:
                if self.is_point_in_polygon(proj, territory):
                    if territory == "North Iran":
                        return "Iran", depth+2.0
                    if territory == "Iran":
                        return "Iran", depth+4.0
                    if territory == "Yemen":
                        return "Yemen", depth

            # Priority 2: Short-Range (Shallow Projections Scan for regional neighbors)
            depth = 0.5
            proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
            for territory in ["Lebanon", "Gaza"]:
                if self.is_point_in_polygon(proj, territory):
                    return territory, depth

        # 2. Last-Resort Heuristics (Proximity fallbacks for single-point or non-linear clusters)
        # MISSION: Iran and Yemen are restricted to VECTOR-ONLY. Fallback logic only maps to the closest regional origin.
        dist_gaza = self.get_distance(centroid, self.origins["Gaza"])
        dist_lebanon = self.get_distance(centroid, self.origins["Lebanon"])

        if dist_gaza < dist_lebanon:
            return "Gaza", self.strategic_depths["Gaza"]
        else:
            return "Lebanon", self.strategic_depths["Lebanon"]

    def get_projected_origin(self, cluster_cities, origin_name, depth=None):
        """Project the PCA vector back toward the launch territory using tactical depth."""
        cnt_lat = sum(c['coords'][0] for c in cluster_cities) / len(cluster_cities)
        cnt_lon = sum(c['coords'][1] for c in cluster_cities) / len(cluster_cities)
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
        if dist_forward > dist_current and len(cluster_cities) <= MIN_IRAN_THRESHOLD:
            v_lat, v_lon = -v_lat, -v_lon

        scalar = depth if depth is not None else self.strategic_depths.get(origin_name, 10.0)
        proj = [cnt_lat + v_lat * scalar, cnt_lon + v_lon * scalar]
        
        # VALIDATION: Ensure the projected point lands inside the detailed tactical silhouette
        if not self.is_point_in_tactical_polygon(proj, origin_name):
            logger.warning(f"UNRELIABLE_PROJECTION_DETECTED: Core check failed for {origin_name} at {proj}. Falling back to standard origin pin.")
            return self.origins.get(origin_name, proj)
            
        return proj

    def analyze_threat(self, cities_raw):
        """Standalone analysis engine for both live alerts and sandbox 'Dry Runs'."""
        city_coords = []
        for c in cities_raw:
            std = standardize_name(c)
            if std in self.dm.city_map:
                city_coords.append({
                    "name": c, 
                    "coords": [self.dm.city_map[std]['lat'], self.dm.city_map[std]['lon']]
                })
        
        if not city_coords:
            return None

        total_unique_cities = len({c['name'] for c in city_coords})
        force_iran_logic = total_unique_cities > MAX_IRAN_THRESHOLD

        # 1. Neighborhood Clustering (Chain-Link)
        raw_clusters = self.cluster(city_coords)
        
        # 2. Strategic Origin Consolidation
        origin_groups = {}
        for cl in raw_clusters:
            org_name, depth = self.get_origin(cl['cities'])
            
            if force_iran_logic:
                # GLOBAL IRAN OVERRIDE: Massive salvos force origin to Iran
                org_name = "Iran"
                depth = self.strategic_depths["Iran"]
            elif org_name in ["Iran", "North Iran"] and len(cl['cities']) <= MIN_IRAN_THRESHOLD:
                # Apply Cluster-Level Threshold for Iranian Origins (Suppress unless vector-confirmed density is high)
                # Force re-attribution to the closest regional territory (Gaza/Lebanon only)
                cnt_coords = [sum(c['coords'][0] for c in cl['cities']) / len(cl['cities']), 
                              sum(c['coords'][1] for c in cl['cities']) / len(cl['cities'])]
                
                d_gaza = self.get_distance(cnt_coords, self.origins["Gaza"])
                d_lebanon = self.get_distance(cnt_coords, self.origins["Lebanon"])
                
                if d_gaza < d_lebanon:
                    org_name = "Gaza"
                    depth = self.strategic_depths["Gaza"]
                else:
                    org_name = "Lebanon"
                    depth = self.strategic_depths["Lebanon"]

            if org_name not in origin_groups:
                origin_groups[org_name] = {"cities": [], "depth": depth}
            
            city_names = {c['name'] for c in origin_groups[org_name]["cities"]}
            for city in cl['cities']:
                if city['name'] not in city_names:
                    origin_groups[org_name]["cities"].append(city)
                    city_names.add(city['name'])
        
        # 3. Final Tactical Mapping
        processed_clusters = []
        trajectories = []
        highlight_origins = []
        
        for org_name, group in origin_groups.items():
            cities = group["cities"]
            depth = group["depth"]
            
            cnt_lat = sum(c['coords'][0] for c in cities) / len(cities)
            cnt_lon = sum(c['coords'][1] for c in cities) / len(cities)
            centroid = [cnt_lat, cnt_lon]
            
            hull = self.get_convex_hull([c['coords'] for c in cities])
            border_entry = self.get_projected_origin(cities, org_name, depth=depth)
            fixed_pin = self.origins[org_name]
            
            trajectories.append({
                "origin": org_name,
                "origin_coords": border_entry,
                "marker_coords": fixed_pin,
                "target_coords": centroid
            })
            processed_clusters.append({
                "origin": org_name,
                "centroid": centroid,
                "cities": cities,
                "hull": hull
            })
            highlight_origins.append({
                "name": "Iran" if org_name == "North Iran" else org_name,
                "coords": fixed_pin
            })

        # Strategic Map Focus
        isr_center = [31.7683, 35.2137]
        main_origin = isr_center
        strategic_zoom = 8
        for i in ["Gaza", "Lebanon", "Iran", "Yemen"]:
            for trajectory in trajectories:
                if trajectory['origin'] == i:
                    main_origin = trajectory['marker_coords']
                    strategic_zoom = self.zoom_levels.get(i, 8)
        
        if len(processed_clusters) < 2:
            # Single Cluster: Strong bias to impact zone, but pull back to Israel if too extreme
            cluster_center = processed_clusters[0]['centroid']
            mid_lat = (cluster_center[0])
            mid_lon = (cluster_center[1])
            strategic_zoom = 10
        else:
            # Multi-Theatrical: Standard theatre-wide focus (Origin to Israel)
            mid_lat = (main_origin[0]*0.35) + (isr_center[0]*0.65)
            mid_lon = (main_origin[1]*0.35) + (isr_center[1]*0.65)
        
        origin_names = sorted(list(origin_groups.keys()))
        display_origins = [("Iran" if o == "North Iran" else o) for o in origin_names]
        title = f"{' & '.join(set(display_origins))} Salvo"

        return {
            "title": title,
            "clusters": processed_clusters,
            "trajectories": trajectories,
            "highlight_origins": highlight_origins,
            "center": [mid_lat, mid_lon],
            "zoom_level": strategic_zoom,
            "all_cities": city_coords
        }

# --- Main Application ---
async def main():
    # 1. IMMEDIATE PORT BINDING (Satisfy Render's Health Check)
    mm = MongoManager(MONGO_URI, DB_NAME, COLLECTION_NAME)
    dm = LamasDataManager()
    engine = TrackingEngine(dm)
    
    ws = WebSocketManager(mm, engine)
    await ws.start()
    
    # 2. SEAMLESS INITIALIZATION (Background loading)
    await dm.load()

    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.oref.org.il/', 'X-Requested-With': 'XMLHttpRequest'}
    last_alert_id = None
    last_alert_time = None
    threat_ended_time = None

    logger.info("Starting monitoring loop...")
    active_salvo = None
    salvo_start_time = 0
    
    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            try:
                now = time.time()

                # Salvo Processing
                if active_salvo and (now - salvo_start_time > 60*5):
                    # Salvo finalized after 5 minutes window
                    await mm.save_salvo(active_salvo)
                    
                    # Broadcast updated history
                    history = await mm.get_history(limit=50)
                    await ws.broadcast({"type": "history_sync", "data": history})
                    
                    logger.info(f"SALVO FINALIZED: {active_salvo['id']} - {len(active_salvo['clusters'])} clusters.")
                    active_salvo = None
                    ws.active_salvo_data = None

                # Timeout logic
                if last_alert_id:
                    if threat_ended_time and (now - threat_ended_time > 10):
                        logger.info("10s Tactical Reset after explicit threat end. Clearing Command Center.")
                        
                        # MISSION: Finalize and save to history before purging memory
                        if active_salvo:
                            await mm.save_salvo(active_salvo)
                            history = await mm.get_history(limit=50)
                            await ws.broadcast({"type": "history_sync", "data": history})

                        await ws.broadcast({"type": "reset"})
                        last_alert_id = None
                        threat_ended_time = None
                        ws.active_salvo_data = None
                        active_salvo = None # MISSION: Clear tactical memory immediately
                    elif last_alert_time and (now - last_alert_time > 300):
                        logger.info("10m Idle Timeout. Resetting dashboard.")
                        await ws.broadcast({"type": "reset"})
                        last_alert_id = None
                        last_alert_time = None
                        ws.active_salvo_data = None

                # --- Tactical Relay Uplink (Single Source of Truth) ---
                RELAY_URL = os.getenv("RELAY_URL")
                RELAY_AUTH_KEY = os.getenv("RELAY_AUTH_KEY")
                
                if not RELAY_URL:
                    if now % 60 < 10:
                        logger.error("CRITICAL_CONFIGURATION_ERROR: RELAY_URL is missing. Mission status: OFFLINE.")
                    await ws.broadcast({
                        "type": "health_status",
                        "status": "OFFLINE",
                        "upstream_source": "NONE",
                        "timestamp": datetime.now(TIMEZONE).isoformat(),
                        "version": VERSION
                    })
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                # Execute Tactical Fetch
                fetched_data = None
                source_used = None
                
                try:
                    start_t = time.time()
                    headers_relay = {"x-relay-auth": RELAY_AUTH_KEY}
                    async with session.get(RELAY_URL, headers=headers_relay, timeout=5) as resp:
                        if resp.status == 200:
                            text = (await resp.text()).lstrip('\ufeff').strip()
                            if text:
                                fetched_data = json.loads(text)
                                source_used = "BARRAGE"
                        else:
                            if now % 30 < 10:
                                logger.warning(f"RELAY_UPLINK_DEGRADED: Status {resp.status}")
                except Exception as e:
                    if now % 30 < 10:
                        logger.warning(f"RELAY_CONNECTION_FAILURE: {str(e)}")

                # --- Real-Time Status & Analytics Broadcast ---
                h_status = "OPERATIONAL" if fetched_data is not None else "DEGRADED"
                
                # Handle Auth Failures explicitly
                if isinstance(fetched_data, dict) and fetched_data.get('error') == 'Unauthorized':
                    logger.error(f"RELAY_AUTH_FAILURE: The provided RELAY_AUTH_KEY was rejected by {source_used}.")
                    h_status = "UNAUTHORIZED"
                    fetched_data = None

                await ws.broadcast({
                    "type": "health_status",
                    "status": h_status,
                    "upstream_source": source_used if fetched_data else "LIVE",
                    "timestamp": datetime.now(TIMEZONE).isoformat(),
                    "version": VERSION
                })

                if fetched_data:
                    # Normalize list-based stream results
                    if isinstance(fetched_data, list):
                        alerts_to_process = fetched_data
                    else:
                        alerts_to_process = [fetched_data] if fetched_data else []

                    for alert_payload in alerts_to_process:
                        if not isinstance(alert_payload, dict):
                            continue

                        # --- MISSION: Ignore Threat-End Status (newsFlash) ---
                        # Skip processing and logging for explicit "end of threat" messages
                        try:
                            alert_type = str(alert_payload.get('type', ''))
                            instructions = str(alert_payload.get('instructions', ''))
                        except:
                            alert_type = ""
                            instructions = ""
                        
                        logger.info(f"Type: {alert_type}, Instructions: {instructions}")
                        
                        if alert_type == "newsFlash" or "האירוע הסתיים" in instructions:
                            if not threat_ended_time and last_alert_id:
                                logger.info(f"THREAT_ENDED_SIGNAL (newsFlash): Resetting dashboard in 10s.")
                                threat_ended_time = now
                            continue
                        elif not alert_type == "missiles":
                            logger.info(f"non missle alert detected skipping")
                            continue
                        alert_id = alert_payload.get('id')
                        # Support both Raw (data) and Wrapper (cities) formats
                        cities_raw = alert_payload.get('data') or alert_payload.get('cities', [])
                        
                        # --- Salvo Tracking Logic ---
                        is_new_id = alert_id and alert_id != last_alert_id
                        has_new_cities = False
                        
                        if active_salvo and alert_id == active_salvo.get("id"):
                            current_names = {c['name'] for c in active_salvo.get("all_cities", [])}
                            if any(c not in current_names for c in cities_raw):
                                has_new_cities = True

                        if alert_id and (is_new_id or has_new_cities or not active_salvo):
                            logger.info(f"ALERT_DETECTED [Source: {source_used}]: ID={alert_id}, Title='{alert_type}', Cities={len(cities_raw)}")
                            
                            # Debug: Log raw payload for verification
                            logger.debug(f"RAW_PAYLOAD: {alert_payload}")

                            # Rocket alert (cat=1 or fallback)
                            last_alert_id = alert_id
                            last_alert_time = now
                            threat_ended_time = None
                            
                            # Analyze the current threat alert
                            analysis = engine.analyze_threat(cities_raw)
                            
                            if analysis:
                                if not active_salvo or (is_new_id and (now - salvo_start_time > 60)):
                                    logger.info(f"INITIALIZING_SALVO: {alert_id}")
                                    active_salvo = {
                                        "id": alert_id,
                                        "time": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                                        "date": datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
                                        "version": VERSION,
                                        "all_cities": []
                                    }
                                    salvo_start_time = now
                                
                                # Add new hits to the rolling salvo
                                all_names = {c['name'] for c in active_salvo["all_cities"]}
                                for city in analysis["all_cities"]:
                                    if city['name'] not in all_names:
                                        active_salvo["all_cities"].append(city)
                                        all_names.add(city['name'])
                                
                                # Strategic Re-calculation
                                try:
                                    full_analysis = engine.analyze_threat([c['name'] for c in active_salvo["all_cities"]])
                                    if full_analysis:
                                        active_salvo.update(full_analysis)
                                        active_salvo["id"] = alert_id 
                                        
                                        msg_data = {"type": "alert", **active_salvo}
                                        ws.active_salvo_data = msg_data
                                        await ws.broadcast(msg_data)
                                        logger.info(f"BROADCAST_SUCCESS: {alert_id} - Unified strategic salvo: {len(active_salvo['all_cities'])} cities.")
                                    else:
                                        logger.warning(f"STRATEGIC_NULL: Analysis returned no trajectories for {len(active_salvo['all_cities'])} cities.")
                                except Exception as inner:
                                    logger.error(f"STRATEGIC_ERROR: {inner}")
                            else:
                                logger.warning(f"MAPPING_FAILURE: Cities {cities_raw} could not be resolved to coordinates.")
                else:
                    # Explicit Log for Auth/Response failures
                    if now % 60 < POLL_INTERVAL:
                        logger.info(f"HEALTH_CHECK [Source: {source_used}]: Relay returned empty or unauthorized response.")

            except Exception as e:
                logger.error(f"Loop error: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("TACTICAL_ENGINE_SHUTDOWN")
