import json
import logging
from datetime import datetime
from aiohttp import web
import aiohttp_cors
from src.utils.config import ALLOWED_ORIGINS, WS_PORT, MISSION_KEY, TIMEZONE

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
        
        # Initial sync: send history + full active_events snapshot
        try:
            history = await self.db.get_history(limit=50)
            await ws.send_str(json.dumps({"type": "history_sync", "data": history, "version": self.version}))
            
            # Send current active events snapshot for late-joiner sync
            if self.active_events:
                events_list = []
                for eid, ev in self.active_events.items():
                    if ev["end_time"] is None:
                        event_data = ev["data"].copy()
                        event_data["id"] = eid
                        events_list.append(event_data)
                
                if events_list:
                    await ws.send_str(json.dumps({
                        "type": "multi_alert",
                        "events": events_list
                    }, ensure_ascii=False))
        except Exception as e:
            logger.error(f"WS_SYNC_ERROR: {e}")

        try:
            async for msg in ws: pass
        finally:
            self.clients.remove(ws)
        return ws

    async def history_handler(self, request):
        type_req = request.query.get("type", "missiles")
        history = await self.db.get_history(alert_type=type_req, limit=50)
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

    async def broadcast(self, data):
        if not self.clients: return
        message = json.dumps(data, ensure_ascii=False)
        for client in list(self.clients):
            try: await client.send_str(message)
            except: self.clients.remove(client)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', self.port).start()
        logger.info(f"TACTICAL_API_SERVICES_LISTENING: Port {self.port}")
