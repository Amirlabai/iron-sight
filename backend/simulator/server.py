import aiohttp
from aiohttp import web
import json
import os
import logging
from datetime import datetime

# --- Configuration ---
PORT = 8081
LOG_FORMAT = '%(asctime)s - SIMULATOR - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("TacticalSimulator")

class TacticalSimulator:
    def __init__(self):
        self.app = web.Application()
        self.current_payload = None
        
        # Simulator Logic Routes
        self.app.router.add_get('/relay', self.relay_handler)
        self.app.router.add_post('/dispatch', self.dispatch_handler)
        self.app.router.add_post('/end', self.terminate_handler)
        
        # Serve the UI
        self.app.router.add_get('/', self.ui_handler)
        # Serve index.html statically if requested by filename
        self.app.router.add_get('/index.html', self.ui_handler)

    async def ui_handler(self, request):
        """Serve the dispatcher UI interface."""
        ui_path = os.path.join(os.path.dirname(__file__), 'index.html')
        if os.path.exists(ui_path):
            return web.FileResponse(ui_path)
        return web.Response(text="Dispatcher UI (index.html) not found in simulator directory.", status=404)

    async def relay_handler(self, request):
        """The mock endpoint polled by main.py."""
        # Return the payload if it exists, otherwise return empty 200 list
        if self.current_payload:
            payload = self.current_payload
            # We wrap the payload in a list as main.py handles both single and list-based responses
            return web.json_response([payload])
        return web.json_response([]) # Success, but no active alerts

    async def dispatch_handler(self, request):
        """Receives alert data from the Dispatcher UI."""
        try:
            data = await request.json()
            cities = data.get("cities", [])
            if not cities:
                return web.json_response({"error": "No cities supplied"}, status=400)

            # Construct the missile alert payload
            self.current_payload = {
                "id": f"sim_{int(datetime.now().timestamp())}",
                "type": "missiles",
                "cities": cities,
                "instructions": "היכנסו למרחב המוגן",
                "time": datetime.now().strftime("%H:%M:%S")
            }
            
            logger.info(f"DISPATCHED: {len(cities)} targets queued for relay.")
            return web.json_response({"status": "success", "payload": self.current_payload})
        except Exception as e:
            logger.error(f"DISPATCH_ERROR: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def terminate_handler(self, request):
        """Injects an explicit 'End of Threat' signal."""
        self.current_payload = {
            "id": f"end_{int(datetime.now().timestamp())}",
            "type": "newsFlash",
            "instructions": "האירוע הסתיים",
            "time": datetime.now().strftime("%H:%M:%S")
        }
        logger.info("TERMINATION_SIGNAL: Threat-end signal queued for relay.")
        return web.json_response({"status": "terminated", "payload": self.current_payload})

    def run(self):
        logger.info(f"TACTICAL DISPATCHER ACTIVE ON http://localhost:{PORT}")
        web.run_app(self.app, port=PORT)

if __name__ == "__main__":
    sim = TacticalSimulator()
    sim.run()
