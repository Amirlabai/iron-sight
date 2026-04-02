import aiohttp
from aiohttp import web
import json
import os
import logging
from datetime import datetime
from collections import deque

# --- Configuration ---
PORT = 8081
LOG_FORMAT = '%(asctime)s - SIMULATOR - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("TacticalSimulator")

class TacticalSimulator:
    def __init__(self):
        self.app = web.Application()
        self.outbound_queue = deque()
        self.active_alerts = {}  # Track active alert IDs for UI icon state
        
        # Simulator Logic Routes
        self.app.router.add_get('/relay', self.relay_handler)
        self.app.router.add_post('/dispatch', self.dispatch_handler)
        self.app.router.add_post('/end', self.terminate_handler)
        self.app.router.add_get('/active', self.active_handler)
        
        # Serve the UI
        self.app.router.add_get('/', self.ui_handler)
        self.app.router.add_get('/index.html', self.ui_handler)

    async def ui_handler(self, request):
        """Serve the dispatcher UI interface."""
        ui_path = os.path.join(os.path.dirname(__file__), 'index.html')
        if os.path.exists(ui_path):
            return web.FileResponse(ui_path)
        return web.Response(text="Dispatcher UI (index.html) not found in simulator directory.", status=404)

    async def relay_handler(self, request):
        """The mock endpoint polled by main.py. Pops all queued payloads."""
        if not self.outbound_queue:
            return web.json_response([])
        
        payloads = list(self.outbound_queue)
        self.outbound_queue.clear()
        return web.json_response(payloads)

    async def dispatch_handler(self, request):
        """Receives alert data from the Dispatcher UI and pushes to outbound queue."""
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
        return web.json_response(self.active_alerts)

    def run(self):
        logger.info(f"TACTICAL DISPATCHER ACTIVE ON http://localhost:{PORT}")
        web.run_app(self.app, port=PORT)

if __name__ == "__main__":
    sim = TacticalSimulator()
    sim.run()
