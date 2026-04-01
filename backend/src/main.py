import asyncio
import aiohttp
import json
import logging
import os
import time
from datetime import datetime
from src.utils.config import POLL_INTERVAL, RELAY_URL, RELAY_AUTH_KEY, TIMEZONE
from src.db.mongo_manager import MongoManager
from src.data.data_manager import LamasDataManager
from src.core.engine import TrackingEngine
from src.core.threat_processor import ThreatProcessor
from src.api.ws_manager import WebSocketManager

# Global Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IronSightTerminal")

# Load Version Info
VERSION = "0.7.0"
try:
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'version.json'), 'r') as f:
        vdata = json.load(f)
        VERSION = vdata.get("version", "0.7.0")
except Exception as e:
    logger.warning(f"VERSION_INIT_FAILURE: {e}")

async def main():
    logger.info(f"IRON SIGHT TACTICAL OPERATING SYSTEM (v{VERSION}) - INITIALIZING")
    
    # Initialize Core Components
    db = MongoManager()
    dm = LamasDataManager()
    engine = TrackingEngine(dm)
    processor = ThreatProcessor(engine)
    ws = WebSocketManager(db, engine, VERSION)
    
    await ws.start()
    await dm.load()

    last_alert_id = None
    last_alert_time = None
    threat_ended_time = None
    active_salvo = None
    salvo_start_time = 0

    async with aiohttp.ClientSession(headers={'User-Agent': 'IronSight/0.6.0'}) as session:
        while True:
            try:
                now = time.time()
                
                # Persistence Sync Timing
                if active_salvo and (now - salvo_start_time > 300):
                    if not active_salvo.get("is_simulation"):
                        await db.save_alert("missiles", active_salvo)
                        history = await db.get_history("missiles", limit=50)
                        await ws.broadcast({"type": "history_sync", "data": history})
                    active_salvo = None
                    ws.active_salvo_data = None

                # Tactical Reset Logics
                if last_alert_id:
                    if threat_ended_time and (now - threat_ended_time > 10):
                        if active_salvo and not active_salvo.get("is_simulation"):
                            await db.save_alert("missiles", active_salvo)
                            history = await db.get_history("missiles", limit=50)
                            await ws.broadcast({"type": "history_sync", "data": history})
                        await ws.broadcast({"type": "reset"})
                        last_alert_id, threat_ended_time, active_salvo, ws.active_salvo_data = None, None, None, None
                    elif last_alert_time and (now - last_alert_time > 300):
                        await ws.broadcast({"type": "reset"})
                        last_alert_id, last_alert_time, ws.active_salvo_data = None, None, None

                # Fetch Tactical Feeds
                if not RELAY_URL: 
                    await asyncio.sleep(POLL_INTERVAL); continue
                
                async with session.get(RELAY_URL, headers={"x-relay-auth": RELAY_AUTH_KEY}, timeout=5) as resp:
                    if resp.status == 200:
                        data = json.loads(await resp.text())
                        alerts = data if isinstance(data, list) else [data] if data else []
                        
                        for alert_payload in alerts:
                            a_type = str(alert_payload.get('type', ''))
                            instructions = str(alert_payload.get('instructions', ''))
                            
                            # Threat End Signal
                            if a_type == "newsFlash" or "האירוע הסתיים" in instructions:
                                if not threat_ended_time and last_alert_id:
                                    threat_ended_time = now
                                continue

                            # Multi-Threat Processing
                            if a_type in ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]:
                                alert_id = alert_payload.get('id')
                                cities_raw = alert_payload.get('data') or alert_payload.get('cities', [])
                                
                                if not alert_id or (alert_id == last_alert_id and a_type != "missiles"):
                                    continue
                                
                                analysis = processor.process(a_type, cities_raw)
                                if analysis:
                                    last_alert_id, last_alert_time, threat_ended_time = alert_id, now, None
                                    is_simulation = alert_payload.get("is_simulation", False)
                                    analysis["is_simulation"] = is_simulation
                                    
                                    if a_type == "missiles":
                                        # Rolling Salvo Support
                                        if not active_salvo or (now - salvo_start_time > 60):
                                            active_salvo = {
                                                "id": alert_id, 
                                                "all_cities": [], 
                                                "time": datetime.now(TIMEZONE).strftime("%H:%M:%S"),
                                                "is_simulation": is_simulation
                                            }
                                            salvo_start_time = now
                                        
                                        existing_names = {c['name'] for c in active_salvo["all_cities"]}
                                        for c in analysis["all_cities"]:
                                            if c['name'] not in existing_names: active_salvo["all_cities"].append(c)
                                        
                                        # Recalculate
                                        full_analysis = processor.process("missiles", [c['name'] for c in active_salvo["all_cities"]])
                                        if full_analysis:
                                            active_salvo.update(full_analysis)
                                            active_salvo["is_simulation"] = is_simulation
                                            ws.active_salvo_data = active_salvo
                                            await ws.broadcast(active_salvo)
                                    else:
                                        # Singular High-Priority Events
                                        analysis["id"] = alert_id
                                        ws.active_salvo_data = analysis
                                        await ws.broadcast(analysis)
                                        
                                        if not is_simulation:
                                            await db.save_alert(a_type, analysis)
                                        
                    await ws.broadcast({
                        "type": "health_status", "status": "OPERATIONAL" if resp.status == 200 else "DEGRADED",
                        "timestamp": datetime.now(TIMEZONE).isoformat(), "version": VERSION
                    })

            except Exception as e:
                logger.error(f"RUNTIME_ERROR: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("SYSTEM_SHUTDOWN")
