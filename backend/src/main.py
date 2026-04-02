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
VERSION = "0.8.0"
try:
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'version.json'), 'r') as f:
        vdata = json.load(f)
        VERSION = vdata.get("version", "0.8.0")
except Exception as e:
    logger.warning(f"VERSION_INIT_FAILURE: {e}")

# Inactivity timeout: events expire after this many seconds of NO updates
INACTIVITY_TIMEOUT = 600  # 5 minutes of silence

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

    # ID-Driven Active Events Dictionary
    # Structure: { alert_id: { "data": <analysis_payload>, "last_update_time": <float>, "end_time": <float|None>, "category": <str> } }
    active_events = {}

    async with aiohttp.ClientSession(headers={'User-Agent': 'IronSight/0.8.0'}) as session:
        while True:
            try:
                now = time.time()
                events_changed = False

                # --- Lifecycle Maintenance ---
                expired_ids = []
                for eid, ev in list(active_events.items()):
                    # Inactivity timeout: only trigger after 5 min of NO updates (last_update_time based)
                    if ev["end_time"] is None and (now - ev["last_update_time"] > INACTIVITY_TIMEOUT):
                        ev["end_time"] = now
                        logger.info(f"EVENT_TIMEOUT: {eid} - No updates for {INACTIVITY_TIMEOUT}s. Marking for termination.")
                        await db.log_event(eid, ev["category"], "TIMEOUT", ev["data"])
                    
                    # End-of-threat grace period (10s after end signal)
                    if ev["end_time"] and (now - ev["end_time"] > 10):
                        # Persist to DB before purging
                        if not ev["data"].get("is_simulation"):
                            try:
                                await db.save_alert(ev["category"], ev["data"])
                                logger.info(f"EVENT_PERSISTED: {eid} ({ev['category']}) - {len(ev['data'].get('all_cities', []))} cities saved to MongoDB.")
                                history = await db.get_history(ev["category"], limit=50)
                                await ws.broadcast({"type": "history_sync", "data": history})
                            except Exception as db_err:
                                logger.error(f"EVENT_PERSIST_FAILURE: {eid} - {db_err}")
                        expired_ids.append(eid)

                for eid in expired_ids:
                    category = active_events[eid]["category"]
                    city_count = len(active_events[eid]["data"].get("all_cities", []))
                    purge_data = active_events[eid]["data"]
                    del active_events[eid]
                    events_changed = True
                    logger.info(f"EVENT_PURGED: {eid} ({category}, {city_count} cities)")
                    await db.log_event(eid, category, "PURGED", purge_data)

                # If events were purged, broadcast updated state
                if events_changed:
                    ws.active_events = active_events
                    await _broadcast_multi_alert(ws, active_events)
                    if not active_events:
                        await ws.broadcast({"type": "reset"})

                # --- Fetch Tactical Feeds ---
                if not RELAY_URL: 
                    await asyncio.sleep(POLL_INTERVAL); continue
                
                try:
                    async with session.get(RELAY_URL, headers={"x-relay-auth": RELAY_AUTH_KEY}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = json.loads(await resp.text())
                            alerts = data if isinstance(data, list) else [data] if data else []
                            
                            for alert_payload in alerts:
                                a_type = str(alert_payload.get('type', ''))
                                instructions = str(alert_payload.get('instructions', ''))
                                alert_id = alert_payload.get('id')
                                
                                # --- Threat End Signal (ID-Targeted) ---
                                if a_type == "newsFlash" or "האירוע הסתיים" in instructions:
                                    if alert_id and alert_id in active_events:
                                        active_events[alert_id]["end_time"] = now
                                        logger.info(f"END_SIGNAL_RECEIVED: {alert_id}")
                                        await db.log_event(alert_id, active_events[alert_id]["category"], "END_SIGNAL", active_events[alert_id]["data"])
                                    elif alert_id is None or alert_id not in active_events:
                                        for eid in active_events:
                                            if active_events[eid]["end_time"] is None:
                                                active_events[eid]["end_time"] = now
                                                await db.log_event(eid, active_events[eid]["category"], "END_SIGNAL", active_events[eid]["data"])
                                        if active_events:
                                            logger.info(f"END_SIGNAL_BROADCAST: All {len(active_events)} active events marked for termination.")
                                    continue

                                # --- Multi-Threat Processing ---
                                if a_type in ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]:
                                    if not alert_id:
                                        continue
                                    
                                    # Protocol Guard: handle both relay data formats
                                    cities_raw = alert_payload.get('data') or alert_payload.get('cities', [])
                                    if isinstance(cities_raw, str):
                                        cities_raw = [cities_raw]
                                    if not cities_raw:
                                        logger.warning(f"EMPTY_PAYLOAD: {alert_id} ({a_type}) - No city data in payload.")
                                        continue
                                    
                                    is_simulation = alert_payload.get("is_simulation", False)

                                    if alert_id in active_events:
                                        # Rolling update: merge new cities into existing event
                                        existing = active_events[alert_id]
                                        existing_names = {c['name'] for c in existing["data"]["all_cities"]}
                                        
                                        analysis = processor.process(a_type, cities_raw)
                                        if analysis:
                                            new_cities = [c for c in analysis["all_cities"] if c['name'] not in existing_names]
                                            for c in new_cities:
                                                existing["data"]["all_cities"].append(c)
                                            
                                            # Recalculate with full city set
                                            full_analysis = processor.process(a_type, [c['name'] for c in existing["data"]["all_cities"]])
                                            if full_analysis:
                                                full_analysis["id"] = alert_id
                                                full_analysis["is_simulation"] = is_simulation
                                                full_analysis["time"] = existing["data"].get("time", datetime.now(TIMEZONE).strftime("%H:%M:%S"))
                                                existing["data"] = full_analysis
                                                existing["end_time"] = None  # Reset any pending end
                                                existing["last_update_time"] = now  # Reset inactivity timer
                                                
                                                total_cities = len(full_analysis.get("all_cities", []))
                                                logger.info(f"ROLLING_UPDATE: {alert_id} ({a_type}) - +{len(new_cities)} new cities. Total: {total_cities}")
                                                await db.log_event(alert_id, a_type, "UPDATED", full_analysis)
                                    else:
                                        # New event
                                        analysis = processor.process(a_type, cities_raw)
                                        if not analysis:
                                            continue
                                        
                                        analysis["id"] = alert_id
                                        analysis["is_simulation"] = is_simulation
                                        analysis["time"] = datetime.now(TIMEZONE).strftime("%H:%M:%S")
                                        
                                        active_events[alert_id] = {
                                            "data": analysis,
                                            "last_update_time": now,
                                            "end_time": None,
                                            "category": a_type
                                        }
                                        
                                        city_count = len(analysis.get("all_cities", []))
                                        logger.info(f"DETECTION_SIGNAL: {alert_id} ({a_type}) - {city_count} cities detected. Active events: {len(active_events)}")
                                        await db.log_event(alert_id, a_type, "DETECTED", analysis)

                                    # Broadcast updated multi-alert state
                                    ws.active_events = active_events
                                    await _broadcast_multi_alert(ws, active_events)
                            
                        await ws.broadcast({
                            "type": "health_status", "status": "OPERATIONAL" if resp.status == 200 else "DEGRADED",
                            "timestamp": datetime.now(TIMEZONE).isoformat(), "version": VERSION
                        })
                except asyncio.TimeoutError:
                    logger.warning("RELAY_TIMEOUT: Upstream relay did not respond within 5s.")
                except aiohttp.ClientError as net_err:
                    logger.error(f"RELAY_CONNECTION_FAILURE: {net_err}")

            except Exception as e:
                logger.error(f"RUNTIME_ERROR: {e}", exc_info=True)
            
            await asyncio.sleep(POLL_INTERVAL)


async def _broadcast_multi_alert(ws, active_events):
    """Push the full active events array to all connected clients."""
    events_list = []
    for eid, ev in active_events.items():
        if ev["end_time"] is None:  # Only broadcast currently active (not ending) events
            event_data = ev["data"].copy()
            event_data["id"] = eid
            events_list.append(event_data)
    
    await ws.broadcast({
        "type": "multi_alert",
        "events": events_list
    })


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("SYSTEM_SHUTDOWN")
