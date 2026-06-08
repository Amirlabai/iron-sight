import json
import logging
import time
from datetime import datetime
from aiohttp import web
import aiohttp_cors
from src.api.history_operator import HistoryOperatorAPI
from src.utils.config import ALLOWED_ORIGINS, WS_PORT, MISSION_KEY, TIMEZONE
from src.utils.cluster_utils import build_merged_payloads
from src.utils.observability import (
    http_observability_middleware,
    log_ws_session,
)

logger = logging.getLogger("IronSightBackend")

class WebSocketManager:
    def __init__(self, db_manager, engine, version, push_manager=None):
        self.port = WS_PORT
        self.db = db_manager
        self.engine = engine
        self.version = version
        self.push_manager = push_manager
        self.clients = set()
        self.app = web.Application(middlewares=[http_observability_middleware])
        self.active_events = {}  # Mirrors main.py's active_events for late-joiner sync

        self.cors = aiohttp_cors.setup(self.app, defaults={
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            ) for origin in ALLOWED_ORIGINS
        })

        self._history = HistoryOperatorAPI(
            self.db,
            self.engine,
            on_history_mutate=self._broadcast_history_sync,
            operator_mode=False,
        )
        self._setup_routes()

    def _setup_routes(self):
        self.add_route("GET", "/ws", self.ws_handler)
        self.add_route("GET", "/", self.health_handler)
        self.add_route("POST", "/api/calibrate", self.calibrate_handler)
        self._history.register_routes(self.add_route)
        self.add_route("GET", "/api/push/vapid-public-key", self.push_vapid_handler)
        self.add_route("POST", "/api/push/subscribe", self.push_subscribe_handler)
        self.add_route("PATCH", "/api/push/location", self.push_location_handler)
        self.add_route("DELETE", "/api/push/unsubscribe", self.push_unsubscribe_handler)

    def add_route(self, method, path, handler):
        resource = self.app.router.add_resource(path)
        self.cors.add(resource.add_route(method, handler))

    async def _broadcast_history_sync(self):
        history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
        await self.broadcast({
            "type": "history_sync", "data": history, "has_more": has_more,
        })

    async def health_handler(self, request):
        return web.json_response({
            "status": "OPERATIONAL",
            "version": self.version,
            "engine": "IRON SIGHT TACTICAL",
            "timestamp": datetime.now(TIMEZONE).isoformat()
        })

    async def push_vapid_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.get_vapid_public_key():
            return web.json_response({"error": "VAPID not configured"}, status=503)
        return web.json_response({"publicKey": pm.get_vapid_public_key()})

    def _push_client_token(self, request, body=None):
        token = request.headers.get("X-Push-Client-Token")
        if not token and body:
            token = body.get("client_token")
        return token

    async def push_subscribe_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.is_configured():
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            ok, err, client_token = await pm.upsert_subscription(body)
            if not ok:
                return web.json_response({"error": err or "Subscribe failed"}, status=400)
            return web.json_response({"status": "subscribed", "client_token": client_token}, status=201)
        except Exception as e:
            logger.error(f"PUSH_SUBSCRIBE_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def push_location_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.is_configured():
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            endpoint = body.get("endpoint")
            loc = body.get("location") or {}
            client_token = self._push_client_token(request, body)
            if not endpoint or loc.get("lat") is None or loc.get("lng") is None:
                return web.json_response({"error": "Missing endpoint or location"}, status=400)
            if not client_token:
                return web.json_response({"error": "Unauthorized"}, status=401)
            result = await pm.update_location(endpoint, loc["lat"], loc["lng"], client_token)
            if result == "unauthorized":
                return web.json_response({"error": "Unauthorized"}, status=401)
            if result == "not_found":
                return web.json_response({"error": "Subscription not found"}, status=404)
            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"PUSH_LOCATION_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def push_unsubscribe_handler(self, request):
        pm = self.push_manager
        if not pm:
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            endpoint = body.get("endpoint")
            client_token = self._push_client_token(request, body)
            if not endpoint:
                return web.json_response({"error": "Missing endpoint"}, status=400)
            if not client_token:
                return web.json_response({"error": "Unauthorized"}, status=401)
            deleted = await pm.delete_subscription(endpoint, client_token)
            if not deleted:
                return web.json_response({"error": "Unauthorized or not found"}, status=401)
            return web.json_response({"status": "unsubscribed"})
        except Exception as e:
            logger.error(f"PUSH_UNSUBSCRIBE_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        sync_started = time.perf_counter()
        history_rows = 0
        active_count = len(self.active_events)

        try:
            history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
            history_rows = len(history)
            await ws.send_str(json.dumps({
                "type": "history_sync",
                "data": history,
                "has_more": has_more,
                "version": self.version,
            }))

            if self.active_events:
                events_list = await build_merged_payloads(self.active_events, self.engine, threshold_km=15)
                if events_list:
                    await ws.send_str(json.dumps({
                        "type": "multi_alert",
                        "events": events_list,
                    }, ensure_ascii=False))
            log_ws_session(
                event="CONNECT",
                client_count=len(self.clients),
                history_rows=history_rows,
                active_events=active_count,
                duration_ms=(time.perf_counter() - sync_started) * 1000,
            )
        except Exception as e:
            log_ws_session(
                event="CONNECT",
                client_count=len(self.clients),
                history_rows=history_rows,
                active_events=active_count,
                duration_ms=(time.perf_counter() - sync_started) * 1000,
                error=e,
            )

        try:
            async for msg in ws:
                pass
        finally:
            self.clients.discard(ws)
            log_ws_session(event="DISCONNECT", client_count=len(self.clients))
        return ws

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
            except: self.clients.discard(client)

    async def start(self):
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        await self._site.start()
        logger.info(f"TACTICAL_API_SERVICES_LISTENING: Port {self.port}")

    async def stop(self):
        runner = getattr(self, "_runner", None)
        if runner is not None:
            await runner.cleanup()
            self._runner = None
