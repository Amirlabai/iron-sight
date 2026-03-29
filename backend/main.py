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

# --- Configuration ---
POLL_INTERVAL = 3       # Seconds between API polls
WS_PORT = int(os.environ.get("PORT", 8080)) # Dynamic port for Deployment
TIMEZONE = ZoneInfo("Asia/Jerusalem")
LAMAS_DATA_URL = "https://raw.githubusercontent.com/idodov/RedAlert/refs/heads/main/apps/red_alerts_israel/lamas_data.json"
LOCAL_DATA_FILE = "lamas_data.json"
HISTORY_FILE = "history.json"
OREF_API_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IronSightBackend")

# --- Utilities ---
@lru_cache(maxsize=1000)
def standardize_name(name):
    if not name: return ""
    name = re.sub(r'[\-\,\(\)\s]+', '', name)
    return name.strip()

# --- WebSocket Manager ---
class WebSocketManager:
    def __init__(self, port=WS_PORT):
        self.port = port
        self.clients = set()
        self.app = web.Application()
        self.app.router.add_get('/ws', self.ws_handler)
        self.runner = None

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        logger.info(f"Client connected. Total: {len(self.clients)}")
        
        # Send current history on connect
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    hist = json.load(f)
                    await ws.send_str(json.dumps({"type": "history_sync", "data": hist}))
        except ConnectionResetError:
            pass # Client disconnected during handshake

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT and msg.data == 'close':
                    await ws.close()
        finally:
            self.clients.remove(ws)
            logger.info(f"Client disconnected. Total: {len(self.clients)}")
        return ws

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
        try:
            with open('tactical_borders.json', 'r') as f:
                self.boundaries = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load tactical_borders.json: {e}")
            # Minimal fallbacks
            self.boundaries = {
                "Gaza": [[31.2, 34.2], [31.6, 34.6], [31.5, 34.5], [31.1, 34.1]],
                "Lebanon": [[33.1, 35.1], [33.5, 35.4], [34.5, 36.1], [34.6, 36.6], [33.9, 36.4], [33.1, 35.5]],
                "Yemen": [[12.6, 43.1], [15.3, 42.6], [17.5, 43.2], [19.0, 48.0], [17.0, 53.0], [13.0, 49.0], [12.6, 43.1]],
                "Iran": [[25.0, 61.0], [30.0, 63.0], [38.0, 63.0], [40.0, 48.0], [40.0, 44.0], [35.0, 45.0], [30.0, 48.0], [25.0, 55.0], [25.0, 61.0]]
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

    def get_origin(self, cluster_cities):
        """Identify origin based on trend vector and geographic cluster centroid."""
        centroid_lat = sum(c['coords'][0] for c in cluster_cities) / len(cluster_cities)
        centroid_lon = sum(c['coords'][1] for c in cluster_cities) / len(cluster_cities)
        
        vector = self.calculate_regression_vector(cluster_cities)
        
        # Tactical Origin Heuristics
        if vector:
            if abs(vector[1]) < 2 and centroid_lat > 32.5: return "Lebanon"
        
        if centroid_lat > 32.7: return "Lebanon"
        if centroid_lat < 31.7 and centroid_lon < 34.6: return "Gaza"
        if centroid_lat < 31.0: return "Yemen"
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
        depths = {
            "Gaza": 0.5,
            "Lebanon": 1,
            "Iran": 18.0,
            "Yemen": 20.0
        }
        scalar = depths.get(origin_name, 10.0)
        
        return [cnt_lat + v_lat * scalar, cnt_lon + v_lon * scalar]

# --- Main Application ---
async def main():
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm)
    ws = WebSocketManager()
    await ws.start()

    # History setup
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except: history = []

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
                    history.insert(0, active_salvo)
                    history = history[:50]
                    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                        json.dump(history, f, ensure_ascii=False, indent=2)
                    
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
                                                "centroid": centroid,
                                                "cities": cities,
                                                "hull": hull
                                            })
                                            highlight_origins.append({
                                                "name": org_name,
                                                "coords": fixed_pin
                                            })

                                        # Strategic Map Focus: Midpoint between Origin Pin and Israel Center
                                        isr_center = [31.7683, 35.2137]
                                        main_origin = trajectories[0]['marker_coords'] if trajectories else isr_center
                                        mid_lat = (main_origin[0] + isr_center[0]) / 2
                                        mid_lon = (main_origin[1] + isr_center[1]) / 2
                                        
                                        is_long_range = any(t['origin'] in ["Yemen", "Iran"] for t in trajectories)
                                        strategic_zoom = 6 if is_long_range else 10

                                        active_salvo.update({
                                            "clusters": processed_clusters,
                                            "trajectories": trajectories,
                                            "highlight_origins": highlight_origins,
                                            "center": [mid_lat, mid_lon],
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
        logger.info("Shutting down...")
