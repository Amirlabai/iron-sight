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

# Load Secrets
load_dotenv()

# --- Configuration ---
POLL_INTERVAL = 3       # Seconds between API polls
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        self.app.router.add_get('/ws', self.ws_handler)
        self.app.router.add_post('/api/calibrate', self.calibrate_handler)
        self.app.router.add_get('/api/history', self.history_handler)
        self.runner = None

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
            # (Note: engine is accessible via global but we should use standard logic)
            zoom_map = {"Gaza": 10, "Lebanon": 8, "Iran": 6, "North Iran": 6, "Yemen": 6}
            strategic_zoom = zoom_map.get(new_origin, 8)
            
            # Use TrackingEngine 
            origin_coords = self.engine.get_capped_origin_coords(cities, new_origin)
            
            # Update the DB
            update_data = {
                "manual_origin": new_origin,
                "trajectories": [{
                    "origin": new_origin,
                    "origin_coords": origin_coords,
                    "target_coords": [mid_lat, mid_lon],
                    "marker_coords": origin_coords
                }],
                "zoom_level": strategic_zoom,
                "center": [(origin_coords[0] + 31.7)/2, (origin_coords[1] + 35.2)/2]
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
        self.collection = self.db[collection_name] if self.db is not None else None

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

    async def load(self):
        if os.path.exists(LOCAL_DATA_FILE):
            with open(LOCAL_DATA_FILE, 'r', encoding='utf-8-sig') as f:
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
            with open(LOCAL_DATA_FILE, 'w', encoding='utf-8-sig') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        for area, cities in data.get('areas', {}).items():
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
        # Load Strategic Boundaries from JSON
        self.boundaries = {}
        # Strategic Pin Aliasing (Always ensure strategic corridors are mapped for pinning)
        self.origins["North Iran"] = self.origins["Iran"]
        
        try:
            with open('tactical_borders.json', 'r') as f:
                self.boundaries = json.load(f)
            logger.info("TACTICAL BOUNDARIES LOADED")
        except Exception as e:
            logger.warning(f"Using fallback boundaries: {e}")
            self.boundaries = {
                "Gaza": [[31.2, 34.2], [31.6, 34.6], [31.5, 34.6], [31.2, 34.3]],
                "Lebanon": [[33.1, 35.1], [33.5, 35.9], [34.7, 36.0], [34.7, 35.8]],
                "Yemen": [[12.6, 43.5], [16.6, 53.1], [19.0, 52.0], [17.5, 43.4]],
                "Iran": [[25.0, 61.0], [38.0, 63.0], [40.0, 44.0], [25.0, 55.0]],
                "North Iran": [[36.8, 53.8], [39.8, 43.8], [33.1, 46.2], [36.8, 53.8]]
            }

    def get_distance(self, c1, c2):
        return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)**0.5

    def get_convex_hull(self, points):
        """Monotone Chain algorithm for Convex Hull."""
        n = len(points)
        if n <= 2: return points
        points.sort()
        upper = []
        for p in points:
            while len(upper) >= 2 and self._cross_product(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        lower = []
        for p in reversed(points):
            while len(lower) >= 2 and self._cross_product(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        return upper[:-1] + lower[:-1]

    def _cross_product(self, o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def is_point_in_polygon(self, point, poly_name):
        """Standard Ray-Casting algorithm for boundary detection."""
        if poly_name not in self.boundaries: return False
        poly = self.boundaries[poly_name]
        x, y = point
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def calculate_regression_vector(self, cities):
        """Find the Dominant Axis of the cluster using PCA (Eigenvectors of Covariance)."""
        if len(cities) < 2: return None
        
        # Deduplicate cities for tactical accuracy (one point per city location)
        unique_coords = list(set(tuple(c['coords']) for c in cities))
        if len(unique_coords) < 2: return None
        
        n = len(unique_coords)
        x = [p[0] for p in unique_coords]
        y = [p[1] for p in unique_coords]
        
        avg_x = sum(x) / n
        avg_y = sum(y) / n
        
        # Mean-centering
        dx = [i - avg_x for i in x]
        dy = [i - avg_y for i in y]
        
        # Covariance Matrix Elements
        cov_xx = sum(i*i for i in dx) / n
        cov_yy = sum(j*j for j in dy) / n
        cov_xy = sum(i*j for i, j in zip(dx, dy)) / n
        
        # Solve for the dominant eigenvalue of [cov_xx, cov_xy; cov_xy, cov_yy]
        # Characteristic eq: (cov_xx - L)(cov_yy - L) - cov_xy^2 = 0
        # L = 0.5 * (trace +/- sqrt(trace^2 - 4*det))
        trace = cov_xx + cov_yy
        det = cov_xx * cov_yy - cov_xy**2
        
        # Use the larger eigenvalue
        L = 0.5 * (trace + (trace**2 - 4*det)**0.5)
        
        # Dominant Eigenvector (V_x, V_y) where (cov_xx - L)V_x + cov_xy*V_y = 0
        if cov_xy != 0:
            v_x = cov_xy
            v_y = L - cov_xx
        else:
            v_x = 1 if cov_xx >= cov_yy else 0
            v_y = 0 if cov_xx >= cov_yy else 1
            
        return [v_x, v_y]

    def cluster(self, cities, threshold_km=30.0):
        deg = threshold_km / 111.0
        clusters = []
        for city in cities:
            added = False
            for cl in clusters:
                # Tactical Chain: Link if within range of ANY cluster member
                if any(self.get_distance(city['coords'], other['coords']) <= deg for other in cl['cities']):
                    cl['cities'].append(city)
                    cl['centroid'] = [
                        sum(c['coords'][0] for c in cl['cities']) / len(cl['cities']),
                        sum(c['coords'][1] for c in cl['cities']) / len(cl['cities'])
                    ]
                    added = True
                    break
            if not added:
                clusters.append({'centroid': city['coords'], 'cities': [city]})
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
            if dist_next < dist_now:
                v_lat, v_lon = -v_lat, -v_lon
                
                # Priority 1: Long-Range (Deep Projections Scan for strategic depth)
                # We scan multiple depths to hit different Iranian/Regional polygons
                for depth in [13.0, 14.0, 16.0, 18.0, 20.0]:
                    proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
                    for territory in ["North Iran", "Iran", "Yemen"]:
                        if self.is_point_in_polygon(proj, territory):
                            return territory

                # Priority 2: Short-Range (Shallow Projections Scan for regional neighbors)
                for depth in [1.5, 2.0, 2.5]:
                    proj = [centroid[0] + v_lat * depth, centroid[1] + v_lon * depth]
                    for territory in ["Lebanon", "Gaza"]:
                        if self.is_point_in_polygon(proj, territory):
                            return territory

        # 2. Last-Resort Heuristics (Proximity fallbacks for single-point or non-linear clusters)
        if centroid[0] > 32.8: return "Lebanon"
        if centroid[0] < 31.7 and centroid[1] < 34.6: return "Gaza"
        if centroid[0] < 31.0: return "Yemen"
        
        return "Iran"

    def get_capped_origin_coords(self, cluster_cities, origin_name):
        """Project the PCA vector as a pure straight line back toward the launch territory."""
        cnt_lat = sum(c['coords'][0] for c in cluster_cities) / len(cluster_cities)
        cnt_lon = sum(c['coords'][1] for c in cluster_cities) / len(cluster_cities)
        vector = self.calculate_regression_vector(cluster_cities)
        
        origin_center = self.origins.get(origin_name, [0, 0])
        if not vector: return origin_center
        
        v_lat, v_lon = vector
        # Normalize vector for consistent projection depth
        mag = (v_lat**2 + v_lon**2)**0.5
        if mag == 0: return origin_center
        v_lat, v_lon = v_lat/mag, v_lon/mag
        # Orient vector toward origin country
        dist_current = self.get_distance([cnt_lat, cnt_lon], origin_center)
        dist_forward = self.get_distance([cnt_lat + v_lat*0.1, cnt_lon + v_lon*0.1], origin_center)
        if dist_forward > dist_current:
            v_lat, v_lon = -v_lat, -v_lon

        # Dynamic Strategic Depth Mapping
        depth_map = {
            "Gaza": 0.5,
            "Lebanon": 1.0,
            "Iran": 18.0,
            "North Iran": 14.0,
            "Yemen": 20.0
        }
        scalar = depth_map.get(origin_name, 10.0)
        
        return [cnt_lat + v_lat * scalar, cnt_lon + v_lon * scalar]

# --- Main Application ---
async def main():
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm)
    
    # Persistence Initialize
    mm = MongoManager(MONGO_URI, DB_NAME, COLLECTION_NAME)
    
    ws = WebSocketManager(mm, engine)
    await ws.start()

    # Database sync status check
    history_snapshot = await mm.get_history(limit=5)
    logger.info(f"Database sync active. Found {len(history_snapshot)} recent salvos.")

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
                if active_salvo and (now - salvo_start_time > 90):
                    # Salvo finalized after 90s window
                    await mm.save_salvo(active_salvo)
                    
                    # Broadcast updated history
                    history = await mm.get_history(limit=50)
                    await ws.broadcast({"type": "history_sync", "data": history})
                    
                    logger.info(f"SALVO FINALIZED: {active_salvo['id']} - {len(active_salvo['clusters'])} clusters.")
                    active_salvo = None

                # Timeout logic
                if last_alert_id:
                    if threat_ended_time and (now - threat_ended_time > 300):
                        logger.info("5m Timeout after explicit threat end. Resetting dashboard.")
                        await ws.broadcast({"type": "reset"})
                        last_alert_id = None
                        threat_ended_time = None
                    elif last_alert_time and (now - last_alert_time > 600):
                        logger.info("10m Idle Timeout. Resetting dashboard.")
                        await ws.broadcast({"type": "reset"})
                        last_alert_id = None
                        last_alert_time = None

                async with session.get(OREF_API_URL) as resp:
                    if resp.status == 200:
                        text = (await resp.text()).lstrip('\ufeff').strip()
                        if not text:
                            await asyncio.sleep(POLL_INTERVAL)
                            continue
                        
                        data = json.loads(text)
                        alert_id = data.get('id')
                        
                        if alert_id != last_alert_id:
                            title = data.get('title', '')
                            
                            if "האירוע הסתיים" in title:
                                if not threat_ended_time and last_alert_id:
                                    logger.info("Official End of Threat detected. Timer started (5m).")
                                    threat_ended_time = now
                                continue

                            # Rocket alert (cat=1)
                            if int(data.get('cat', 1)) == 1:
                                last_alert_id = alert_id
                                last_alert_time = now
                                threat_ended_time = None
                                
                                cities_raw = data.get('data', [])
                                city_coords = []
                                for c in cities_raw:
                                    std = standardize_name(c)
                                    if std in dm.city_map:
                                        city_coords.append({"name": c, "coords": [dm.city_map[std]['lat'], dm.city_map[std]['lon']]})
                                
                                    if city_coords:
                                        # Initialize salvo cities if new
                                        if not active_salvo or (now - salvo_start_time > 60):
                                            active_salvo = {
                                                "id": alert_id,
                                                "time": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                                                "date": datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
                                                "title": "Tactical Alert", # Default, updated below
                                                "version": VERSION,
                                                "all_cities": []
                                            }
                                            salvo_start_time = now
                                        
                                        # Merge current alert cities into salvo
                                        active_salvo["all_cities"].extend(city_coords)
                                        
                                        # 1. Neighborhood Clustering (Chain-Link)
                                        raw_clusters = engine.cluster(active_salvo["all_cities"])
                                        
                                        # 2. Strategic Origin Consolidation: Merge everything from the same country
                                        origin_groups = {}
                                        for cl in raw_clusters:
                                            org_name = engine.get_origin(cl['cities'])
                                            if org_name not in origin_groups:
                                                origin_groups[org_name] = []
                                            
                                            # Deduplicate cities within the strategic group for tactical accuracy
                                            city_names = {c['name'] for c in origin_groups[org_name]}
                                            for city in cl['cities']:
                                                if city['name'] not in city_names:
                                                    origin_groups[org_name].append(city)
                                                    city_names.add(city['name'])
                                        
                                        # 3. Final Tactical Mapping
                                        processed_clusters = []
                                        trajectories = []
                                        highlight_origins = []
                                        
                                        for org_name, cities in origin_groups.items():
                                            # Group centroid
                                            cnt_lat = sum(c['coords'][0] for c in cities) / len(cities)
                                            cnt_lon = sum(c['coords'][1] for c in cities) / len(cities)
                                            centroid = [cnt_lat, cnt_lon]
                                            
                                            hull = engine.get_convex_hull([c['coords'] for c in cities])
                                            border_entry = engine.get_capped_origin_coords(cities, org_name)
                                            fixed_pin = engine.origins[org_name]
                                            
                                            trajectories.append({
                                                "origin": org_name,
                                                "origin_coords": border_entry, # Starting point of line
                                                "marker_coords": fixed_pin,    # Fixed location for Label/Pin
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

                                        # Strategic Map Focus: Midpoint between Origin Pin and Israel Center
                                        isr_center = [31.7683, 35.2137]
                                        main_origin = trajectories[0]['marker_coords'] if trajectories else isr_center
                                        mid_lat = (main_origin[0] + isr_center[0]) / 2
                                        mid_lon = (main_origin[1] + isr_center[1]) / 2
                                        
                                        # Granular Strategic Zoom & Framing
                                        zoom_map = {
                                            "Gaza": 10,
                                            "Lebanon": 8,
                                            "Iran": 6,
                                            "North Iran": 6,
                                            "Yemen": 6
                                        }
                                        strategic_zoom = zoom_map.get(list(origin_groups.keys())[0], 8)
                                        salvo_center = [mid_lat, mid_lon]

                                        # Final Metadata Enrichment
                                        origin_names = sorted(list(origin_groups.keys()))
                                        display_origins = [("Iran" if o == "North Iran" else o) for o in origin_names]
                                        active_salvo["title"] = f"{' & '.join(set(display_origins))} Salvo"
                                        
                                        active_salvo.update({
                                            "clusters": processed_clusters,
                                            "trajectories": trajectories,
                                            "highlight_origins": highlight_origins,
                                            "center": salvo_center,
                                            "zoom_level": strategic_zoom
                                        })

                                        await ws.broadcast({"type": "alert", **active_salvo})
                                        logger.info(f"BROADCAST: {alert_id} - UNIFIED STRATEGIC SALVO: {len(active_salvo['all_cities'])} hits.")

            except Exception as e:
                logger.error(f"Loop error: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("TACTICAL_ENGINE_SHUTDOWN")
