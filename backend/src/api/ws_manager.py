import json
import logging
from datetime import datetime
from aiohttp import web
import aiohttp_cors
from src.utils.config import ALLOWED_ORIGINS, WS_PORT, MISSION_KEY, TIMEZONE
from src.utils.cluster_utils import build_merged_payloads

logger = logging.getLogger("IronSightBackend")

class WebSocketManager:
    def __init__(self, db_manager, engine, version):
        self.port = WS_PORT
        self.db = db_manager
        self.engine = engine
        self.version = version
        self.clients = set()
        self.app = web.Application()
        self.active_events = {}  # Mirrors main.py's active_events for late-joiner sync
        
        self.cors = aiohttp_cors.setup(self.app, defaults={
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            ) for origin in ALLOWED_ORIGINS
        })

        self._setup_routes()

    def _setup_routes(self):
        self.add_route("GET", "/ws", self.ws_handler)
        self.add_route("GET", "/", self.health_handler)
        self.add_route("POST", "/api/calibrate", self.calibrate_handler)
        self.add_route("GET", "/api/history", self.history_handler)
        self.add_route("GET", "/api/cities", self.cities_handler)
        self.add_route("POST", "/api/history/update", self.update_history_handler)
        self.add_route("POST", "/api/history/split", self.split_history_handler)

    def add_route(self, method, path, handler):
        resource = self.app.router.add_resource(path)
        self.cors.add(resource.add_route(method, handler))

    async def health_handler(self, request):
        return web.json_response({
            "status": "OPERATIONAL",
            "version": self.version,
            "engine": "IRON SIGHT TACTICAL",
            "timestamp": datetime.now(TIMEZONE).isoformat()
        })

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        
        # Initial sync: send history + merged active_events snapshot
        try:
            history = await self.db.get_consolidated_history(limit=50)
            await ws.send_str(json.dumps({"type": "history_sync", "data": history, "version": self.version}))
            
            # Late-Joiner Sync: run the SAME merge pipeline as the live broadcast
            if self.active_events:
                events_list = await build_merged_payloads(self.active_events, self.engine, threshold_km=15)
                
                if events_list:
                    logger.info(f"LATE_JOINER_SYNC: Sending {len(events_list)} merged event(s) to new client.")
                    await ws.send_str(json.dumps({
                        "type": "multi_alert",
                        "events": events_list
                    }, ensure_ascii=False))
        except Exception as e:
            logger.error(f"WS_SYNC_ERROR: {e}")

        try:
            async for msg in ws: pass
        finally:
            self.clients.discard(ws)
        return ws

    async def history_handler(self, request):
        # Support both 'category' (new protocol) and 'type' (legacy)
        category = request.query.get("category") or request.query.get("type")
        if category:
            history = await self.db.get_history(alert_type=category, limit=50)
        else:
            history = await self.db.get_consolidated_history(limit=50)
        return web.json_response(history)

    async def cities_handler(self, request):
        return web.json_response(self.engine.dm.areas)

    async def calibrate_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            return web.json_response({"status": "SUCCESS"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def update_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            alert_id = data.get("id")
            alert_type = data.get("category")
            origin_name = data.get("origin_name")
            marker_coords = data.get("origin_coords") # Usually from UI drag
            
            if not all([alert_id, alert_type, origin_name, marker_coords]):
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            # Fetch existing to recalculate
            existing = await self.db.get_alert(alert_id, alert_type)
            if not existing:
                return web.json_response({"error": "Alert not found"}, status=404)

            # 1. Update Title and Origin labels
            display_origin = "Iran" if origin_name == "North Iran" else origin_name
            existing["title"] = f"{display_origin} Salvo" if alert_type == "missiles" else existing["title"]
            existing["verified"] = True
            
            # Update Zoom Level (root and trajectory for dual-consumer compatibility)
            zoom = self.engine.zoom_levels.get(origin_name, self.engine.zoom_levels.get("Iran", 6) if "Iran" in origin_name else 8)
            existing["zoom_level"] = zoom

            # 2. Update Clusters
            if existing.get("clusters"):
                for cluster in existing["clusters"]:
                    cluster["origin"] = origin_name

            # 3. Recalculate Trajectory Entry Point if Missiles
            if alert_type == "missiles" and existing.get("trajectories"):
                traj = existing["trajectories"][0]
                traj["origin"] = origin_name
                traj["marker_coords"] = marker_coords
                traj["zoom"] = zoom # Dashboard history expects this here
                
                # RECALCULATE entry point on border
                depth = self.engine.strategic_depths.get(origin_name, 10.0)
                border_entry = self.engine.get_projected_origin(existing["all_cities"], origin_name, depth=depth)
                traj["origin_coords"] = border_entry
                logger.info(f"HISTORY_RECALC: {alert_id} trajectory recalculated for {origin_name} (Border entry: {border_entry})")

            # 4. Commit FULL synchronized payload
            await self.db.save_alert(alert_type, existing)
            
            logger.info(f"HISTORY_FIXED_FULL: {alert_id} ({alert_type}) synchronized to {origin_name} by operator.")
            # Broadcast history refresh
            history = await self.db.get_consolidated_history(limit=50)
            await self.broadcast({"type": "history_sync", "data": history})
            return web.json_response({"status": "SUCCESS", "event": existing})
            
        except Exception as e:
            logger.error(f"HISTORY_UPDATE_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def split_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            alert_id = data.get("id")
            alert_type = data.get("category")
            
            if not all([alert_id, alert_type]):
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            success = await self.db.split_alert(alert_type, alert_id)
            if success:
                logger.info(f"HISTORY_SPLIT: {alert_id} ({alert_type}) removed for re-processing.")
                # Broadcast history refresh
                history = await self.db.get_consolidated_history(limit=50)
                await self.broadcast({"type": "history_sync", "data": history})
                return web.json_response({"status": "SUCCESS"})
            else:
                return web.json_response({"error": "Split failed"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def broadcast(self, data):
        if not self.clients: return
        message = json.dumps(data, ensure_ascii=False)
        for client in list(self.clients):
            try: await client.send_str(message)
            except: self.clients.discard(client)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', self.port).start()
        logger.info(f"TACTICAL_API_SERVICES_LISTENING: Port {self.port}")
