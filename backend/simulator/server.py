"""
Local tactical alert simulator (dev only).

Run with IRON_SIGHT_DEV=1. Point main.py RELAY_URL at http://127.0.0.1:8081/relay
using the same RELAY_AUTH_KEY. Do not use production MONGO_URI or VAPID with sim relay.
"""

import aiohttp
from aiohttp import web
import json
import os
import sys
import logging
from datetime import datetime
from collections import deque
from dotenv import load_dotenv

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

# --- Configuration ---
PORT = 8081
HOST = "127.0.0.1"
LOG_FORMAT = '%(asctime)s - SIMULATOR - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("TacticalSimulator")

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _is_dev_environment() -> bool:
    return os.getenv("IRON_SIGHT_DEV") == "1" or os.getenv("ENV", "").lower() == "development"


def _client_is_loopback(request: web.Request) -> bool:
    peer = request.remote or ""
    if peer in _LOOPBACK_HOSTS:
        return True
    if peer.startswith("127."):
        return True
    return False


def _relay_auth_ok(request: web.Request) -> bool:
    expected = os.getenv("RELAY_AUTH_KEY", "")
    if not expected:
        logger.warning("RELAY_AUTH_KEY unset — /relay rejects all requests")
        return False
    return request.headers.get("x-relay-auth") == expected


def _simulator_token_ok(request: web.Request) -> bool:
    expected = os.getenv("SIMULATOR_DEV_TOKEN", "")
    if not expected:
        return True
    return request.headers.get("X-Simulator-Token") == expected


def _require_local_dev(request: web.Request) -> web.Response | None:
    if not _client_is_loopback(request):
        return web.json_response({"error": "Forbidden: localhost only"}, status=403)
    if not _simulator_token_ok(request):
        return web.json_response({"error": "Forbidden: invalid simulator token"}, status=403)
    return None


class TacticalSimulator:
    def __init__(self):
        self.app = web.Application()
        self.outbound_queue = deque()
        self.active_alerts = {}  # Track active alert IDs for UI icon state
        self._http_session = None
        
        # Simulator Logic Routes
        self.app.router.add_get('/relay', self.relay_handler)
        self.app.router.add_get('/api/cities', self.cities_proxy_handler)
        self.app.router.add_post('/dispatch', self.dispatch_handler)
        self.app.router.add_post('/end', self.terminate_handler)
        self.app.router.add_get('/active', self.active_handler)
        
        # Serve the UI
        self.app.router.add_get('/', self.ui_handler)
        self.app.router.add_get('/index.html', self.ui_handler)
        self.app.on_cleanup.append(self._close_http_session)

    async def _get_http_session(self):
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._http_session

    async def _close_http_session(self, _app):
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def ui_handler(self, request):
        """Serve the dispatcher UI interface."""
        denied = _require_local_dev(request)
        if denied:
            return denied
        ui_path = os.path.join(os.path.dirname(__file__), 'index.html')
        if os.path.exists(ui_path):
            return web.FileResponse(ui_path)
        return web.Response(text="Dispatcher UI (index.html) not found in simulator directory.", status=404)

    async def cities_proxy_handler(self, request):
        """Same-origin proxy to the tactical engine city list (avoids browser CORS)."""
        denied = _require_local_dev(request)
        if denied:
            return denied
        backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8080")
        try:
            session = await self._get_http_session()
            async with session.get(f"{backend_url.rstrip('/')}/api/cities") as resp:
                if resp.status != 200:
                    logger.error(f"CITIES_PROXY: backend returned {resp.status}")
                    return web.json_response(
                        {"error": f"Backend not responding ({backend_url})"},
                        status=502,
                    )
                data = await resp.json()
                return web.json_response(data)
        except aiohttp.ClientError as e:
            logger.error(f"CITIES_PROXY_ERROR: {e!r}")
            return web.json_response(
                {"error": f"Backend unreachable ({backend_url})"},
                status=502,
            )

    async def relay_handler(self, request):
        """The mock endpoint polled by main.py. Pops all queued payloads."""
        if not _relay_auth_ok(request):
            return web.json_response([], status=401)
        if not self.outbound_queue:
            return web.json_response([])
        
        payloads = list(self.outbound_queue)
        self.outbound_queue.clear()
        return web.json_response(payloads)

    async def dispatch_handler(self, request):
        """Receives alert data from the Dispatcher UI and pushes to outbound queue."""
        denied = _require_local_dev(request)
        if denied:
            return denied
        try:
            data = await request.json()
            cities = data.get("cities", [])
            alert_type = data.get("type", "missiles")
            
            if not cities:
                return web.json_response({"error": "No cities supplied"}, status=400)

            alert_id = f"sim_{alert_type}_{int(datetime.now().timestamp())}"
            
            payload = {
                "id": alert_id,
                "is_simulation": True,
                "type": alert_type,
                "cities": cities,
                "instructions": "היכנסו למרחב המוגן",
                "time": datetime.now().strftime("%H:%M:%S")
            }
            
            self.outbound_queue.append(payload)
            self.active_alerts[alert_id] = {
                "type": alert_type,
                "cities": cities,
                "time": payload["time"]
            }
            
            logger.info(f"DISPATCHED [{alert_type}]: {len(cities)} targets queued as {alert_id}.")
            return web.json_response({"status": "success", "payload": payload})
        except Exception as e:
            logger.error(f"DISPATCH_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def terminate_handler(self, request):
        """Injects an explicit 'End of Threat' signal for a specific alert ID."""
        denied = _require_local_dev(request)
        if denied:
            return denied
        try:
            data = await request.json()
            target_id = data.get("id")
        except Exception:
            target_id = None

        if target_id and target_id in self.active_alerts:
            # Targeted termination for a specific alert
            end_payload = {
                "id": target_id,
                "is_simulation": True,
                "type": "newsFlash",
                "instructions": "האירוע הסתיים",
                "time": datetime.now().strftime("%H:%M:%S")
            }
            self.outbound_queue.append(end_payload)
            del self.active_alerts[target_id]
            logger.info(f"TERMINATION_SIGNAL: End queued for alert {target_id}.")
            return web.json_response({"status": "terminated", "id": target_id})
        else:
            # Terminate ALL active alerts
            for aid in list(self.active_alerts.keys()):
                end_payload = {
                    "id": aid,
                    "is_simulation": True,
                    "type": "newsFlash",
                    "instructions": "האירוע הסתיים",
                    "time": datetime.now().strftime("%H:%M:%S")
                }
                self.outbound_queue.append(end_payload)
            terminated_ids = list(self.active_alerts.keys())
            self.active_alerts.clear()
            logger.info(f"TERMINATION_SIGNAL: End queued for ALL alerts: {terminated_ids}.")
            return web.json_response({"status": "terminated_all", "ids": terminated_ids})

    async def active_handler(self, request):
        """Returns currently active alert IDs for the UI to render icons."""
        denied = _require_local_dev(request)
        if denied:
            return denied
        return web.json_response(self.active_alerts)

    def run(self):
        logger.info(f"TACTICAL DISPATCHER ACTIVE ON http://{HOST}:{PORT}")
        web.run_app(self.app, host=HOST, port=PORT)


if __name__ == "__main__":
    if not _is_dev_environment():
        logger.error(
            "Refusing to start: set IRON_SIGHT_DEV=1 or ENV=development for local simulator only."
        )
        sys.exit(1)
    sim = TacticalSimulator()
    sim.run()
