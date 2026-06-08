import asyncio
import aiohttp
import json
import logging
import os
import time
from datetime import datetime
from src.utils.config import POLL_INTERVAL, RELAY_URL, RELAY_AUTH_KEY, TIMEZONE, VAPID_CLAIMS_EMAIL
from src.db.mongo_manager import MongoManager
from src.data.data_manager import LamasDataManager
from src.core.engine import TrackingEngine
from src.core.event_store import EventStore
from src.core.threat_processor import ThreatProcessor
from src.api.ws_manager import WebSocketManager
from src.services.push_manager import PushManager
from src.services.telegram_notifier import TelegramNotifier
from src.utils.kfar_kama import collect_active_track_ids
from src.utils.cluster_utils import build_merged_payloads, group_events, merge_event_group
from src.utils.outbound_policy import relay_upstream_label

# Global Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s')
logger = logging.getLogger("IronSightTerminal")

# Load Version Info
VERSION = "0.0.0"
try:
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'version.json'), 'r') as f:
        vdata = json.load(f)
        VERSION = vdata.get("version", "0.0.0")
except Exception as e:
    logger.warning(f"VERSION_INIT_FAILURE: {e}")

# Inactivity timeout: events expire after this many seconds of NO updates
INACTIVITY_TIMEOUT = 1200  # 20 minutes of silence

async def main():
    logger.info(f"IRON SIGHT TACTICAL OPERATING SYSTEM (v{VERSION}) - INITIALIZING")
    if VAPID_CLAIMS_EMAIL == "mailto:ops@iron-sight.local":
        logger.warning("VAPID_CLAIMS_EMAIL is default placeholder — set a real contact in production.")

    # Initialize Core Components
    db = MongoManager()
    await db.ensure_push_indexes()
    dm = LamasDataManager()
    engine = TrackingEngine(dm, db)
    processor = ThreatProcessor(engine)
    push_manager = PushManager(db)
    telegram_notifier = TelegramNotifier()
    ws = WebSocketManager(db, engine, VERSION, push_manager)
    
    await ws.start()
    await dm.load()

    store = EventStore()
    memory_log_counter = 0

    try:
        async with aiohttp.ClientSession(headers={'User-Agent': 'IronSight/0.0.0'}) as session:
            while True:
                try:
                    now = time.time()
                    events_changed = False

                    # --- Cluster-Aware Lifecycle Maintenance ---
                    active_events = store.active_events
                    all_groups = group_events(active_events, include_all=True) # All groups including ended
                
                    purged_ids = []
                    for group_ids in all_groups:
                        members = [active_events[gid] for gid in group_ids if gid in active_events]
                        if not members: continue
                    
                        # 1. Inactivity Timeout (Unchanged)
                        for gid in group_ids:
                            ev = active_events[gid]
                            if ev["end_time"] is None and (now - ev["last_update_time"] > INACTIVITY_TIMEOUT):
                                store.set_field(gid, "end_time", now)
                                if ev.get("category") == "newsFlash" and not ev.get("lifecycle_status"):
                                    store.set_field(gid, "lifecycle_status", "ended")
                                active_events = store.active_events
                                ev = active_events[gid]
                                logger.info(f"EVENT_TIMEOUT: {gid} - Silence depth exceeded. Marking for termination.")
                                if not ev["data"].get("is_simulation"):
                                    await db.log_event(gid, ev["category"], "TIMEOUT", ev["data"])
                                await _telegram_kfar_kama_ended(telegram_notifier, gid, ev["data"])

                        # 2. Group Persistence Check
                        # Trigger if ALL members have an end_time AND at least one passed 10s grace
                        all_ended = all(m["end_time"] is not None for m in members)
                        any_expired = any(m["end_time"] and (now - m["end_time"] > 10) for m in members)
                    
                        if all_ended and any_expired:
                            # Generate Unified Master Payload
                            master_payload = await merge_event_group(
                                group_ids, active_events, engine, use_polygon_hulls=True
                            )
                        
                            has_persistent = any(
                                not active_events[gid].get("is_transient")
                                for gid in group_ids if gid in active_events
                            )

                            for gid in group_ids:
                                ev_ref = active_events.get(gid)
                                if not ev_ref or not ev_ref.get("is_transient"):
                                    continue
                                if ev_ref["data"].get("is_simulation"):
                                    continue
                                nf_payload = dict(ev_ref["data"])
                                nf_payload["id"] = gid
                                nf_payload["category"] = "newsFlash"
                                nf_payload["lifecycle_status"] = ev_ref.get("lifecycle_status", "ended")
                                try:
                                    await db.save_alert("newsFlash", nf_payload)
                                    logger.info(f"NEWSFLASH_PERSISTED: {gid} status={nf_payload['lifecycle_status']}")
                                except Exception as db_err:
                                    logger.error(f"NEWSFLASH_PERSIST_FAILURE: {gid} - {db_err}")

                            if (
                                master_payload
                                and has_persistent
                                and not master_payload.get("is_simulation")
                                and master_payload.get("category") != "newsFlash"
                            ):
                                try:
                                    await db.save_alert(master_payload["category"], master_payload)
                                    logger.info(f"CLUSTER_PERSISTED: {len(group_ids)} IDs unified -> {master_payload['id']}")
                                    history = await db.get_consolidated_history(limit=50)
                                    await ws.broadcast({"type": "history_sync", "data": history})
                                except Exception as db_err:
                                    logger.error(f"CLUSTER_PERSIST_FAILURE: {master_payload['id']} - {db_err}")
                            elif not has_persistent:
                                try:
                                    history = await db.get_consolidated_history(limit=50)
                                    await ws.broadcast({"type": "history_sync", "data": history})
                                except Exception as db_err:
                                    logger.error(f"NEWSFLASH_HISTORY_SYNC_FAILURE: {db_err}")
                        
                            # Purge all IDs in the group simultaneously
                            for gid in group_ids:
                                purge_ev = active_events[gid]
                                category = purge_ev["category"]
                                city_count = len(purge_ev["data"].get("all_cities", []))
                            
                                if not purge_ev["data"].get("is_simulation"):
                                    await db.log_event(gid, category, "PURGED", purge_ev["data"])
                                await _telegram_kfar_kama_ended(telegram_notifier, gid, purge_ev["data"])
                                store.pop(gid)
                                purged_ids.append(gid)
                                logger.info(f"EVENT_PURGED: {gid} ({category}, {city_count} cities)")
                
                    if purged_ids:
                        events_changed = True

                    # If events were purged, broadcast updated state
                    if events_changed:
                        ws.active_events = store.active_events
                        await _broadcast_multi_alert(ws, store, engine, push_manager, telegram_notifier)
                        if not store:
                            await ws.broadcast({"type": "reset"})

                    # --- Fetch Tactical Feeds ---
                    if not RELAY_URL: 
                        await asyncio.sleep(POLL_INTERVAL); continue
                
                    try:
                        async with session.get(RELAY_URL, headers={"x-relay-auth": RELAY_AUTH_KEY}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                data = json.loads(await resp.text())
                                alerts = data if isinstance(data, list) else [data] if data else []
                            
                                # Pre-scan: strategic mode is enabled only by warning-shaped newsFlash payloads
                                has_newsflash_in_batch = any(
                                    a.get('type') == 'newsFlash' and (a.get('data') or a.get('cities'))
                                    for a in alerts
                                )
                                relay_batch_changed = False
                                active_events = store.active_events

                                for alert_payload in alerts:
                                    a_type = str(alert_payload.get('type', ''))
                                    instructions = str(alert_payload.get('instructions', ''))
                                    alert_id = alert_payload.get('id')
                                
                                    # --- newsFlash Warning OR Threat End Signal (ID-Targeted) ---
                                    is_warning = a_type == "newsFlash" and (alert_payload.get('data') or alert_payload.get('cities'))
                                    is_clearance = "האירוע הסתיים" in instructions or (a_type == "newsFlash" and not is_warning)

                                    if is_clearance:
                                        target_ended_cities = []
                                        # Parse instructions against geographical nomenclature
                                        for area, cities_dict in dm.areas.items():
                                            if area in instructions:
                                                target_ended_cities.extend(cities_dict.keys())
                                            
                                        for city in dm.city_map.keys():
                                            if city in instructions:
                                                target_ended_cities.append(city)
                                            
                                        ended_ids = []
                                        if target_ended_cities:
                                            target_set = set(target_ended_cities)
                                            target_regions_log = []
                                            for eid, ev in active_events.items():
                                                if ev["end_time"] is None:
                                                    ev_cities = {c['name'] for c in ev["data"].get("all_cities", [])}
                                                    if ev_cities and ev_cities.issubset(target_set):
                                                        ended_ids.append(eid)
                                        
                                            for eid in ended_ids:
                                                store.set_field(eid, "end_time", now)
                                                if store.get(eid, {}).get("category") == "newsFlash":
                                                    store.set_field(eid, "lifecycle_status", "cleared")
                                                ev = store.get(eid, {})
                                                logger.info(f"GRANULAR_END_SIGNAL: {eid} terminated based on region match in newsFlash.")
                                                if not ev.get("data", {}).get("is_simulation"):
                                                    await db.log_event(eid, ev["category"], "END_SIGNAL", ev["data"])
                                                await _telegram_kfar_kama_ended(
                                                    telegram_notifier, eid, ev["data"],
                                                )
                                            if ended_ids:
                                                relay_batch_changed = True
                                            
                                        if not ended_ids:
                                            if alert_id and alert_id in store:
                                                store.set_field(alert_id, "end_time", now)
                                                if store.get(alert_id, {}).get("category") == "newsFlash":
                                                    store.set_field(alert_id, "lifecycle_status", "cleared")
                                                logger.info(f"END_SIGNAL_RECEIVED: {alert_id}")
                                                ev = store.get(alert_id, {})
                                                if not ev.get("data", {}).get("is_simulation"):
                                                    await db.log_event(alert_id, ev["category"], "END_SIGNAL", ev["data"])
                                                await _telegram_kfar_kama_ended(
                                                    telegram_notifier, alert_id, ev["data"],
                                                )
                                            elif alert_id is None or alert_id not in store:
                                                for eid, ev in store.items():
                                                    if ev["end_time"] is None:
                                                        store.set_field(eid, "end_time", now)
                                                        if ev.get("category") == "newsFlash":
                                                            store.set_field(eid, "lifecycle_status", "cleared")
                                                        if not ev["data"].get("is_simulation"):
                                                            await db.log_event(eid, ev["category"], "END_SIGNAL", ev["data"])
                                                        await _telegram_kfar_kama_ended(
                                                            telegram_notifier, eid, ev["data"],
                                                        )
                                                if store:
                                                    logger.info(f"END_SIGNAL_BROADCAST: All {len(store)} active events marked for termination.")
                                        relay_batch_changed = True
                                        continue

                                    # --- Multi-Threat Processing ---
                                    if a_type in ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake", "newsFlash"]:
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
                                        analysis = await processor.process(
                                            a_type,
                                            cities_raw,
                                            store.active_events,
                                            has_newsflash_in_batch,
                                            use_polygon_hulls=False,
                                        )
                                        if not analysis:
                                            continue

                                        # Superseding Logic: Actual missiles supersede overlapping newsFlash ghosts
                                        if a_type == "missiles":
                                            incoming_cities = {c['name'] for c in analysis.get("all_cities", [])}
                                            for gid, gv in list(store.items()):
                                                if gv["category"] == "newsFlash" and gv["end_time"] is None:
                                                    gv_cities = {c['name'] for c in gv["data"].get("all_cities", [])}
                                                    if gv_cities.intersection(incoming_cities):
                                                        store.set_field(gid, "end_time", now)
                                                        store.set_field(gid, "lifecycle_status", "superseded")
                                                        logger.info(f"NEWSFLASH_SUPERSEDED: {gid} terminated by incoming missile alert {alert_id}")
                                                        if not gv["data"].get("is_simulation") and not is_simulation:
                                                            await db.log_event(gid, "newsFlash", "SUPERSEDED", gv["data"])
                                                        await _telegram_kfar_kama_ended(telegram_notifier, gid, gv["data"])
                                                        relay_batch_changed = True

                                        event_time = (
                                            alert_payload.get("alertDate", "").replace(" ", "T")
                                            or datetime.now(TIMEZONE).isoformat()
                                        )

                                        if alert_id in store:
                                            changed, new_count, total_cities = await store.apply_rolling_update(
                                                alert_id,
                                                analysis,
                                                a_type,
                                                is_simulation,
                                                event_time,
                                                now,
                                                processor,
                                                has_newsflash_in_batch,
                                            )
                                            if changed:
                                                master_id = store.get(alert_id, {}).get("master_id", alert_id)
                                                full_analysis = store.master_data_for_persist(master_id)
                                                logger.info(
                                                    f"ROLLING_UPDATE: {alert_id} ({a_type}) - "
                                                    f"+{new_count} new cities. Total: {total_cities}"
                                                )
                                                if not is_simulation and full_analysis:
                                                    await db.log_event(alert_id, a_type, "UPDATED", full_analysis)
                                                relay_batch_changed = True
                                        else:
                                            analysis["id"] = alert_id
                                            city_count = await store.register_detection(
                                                alert_id,
                                                analysis,
                                                a_type,
                                                is_simulation,
                                                event_time,
                                                now,
                                                processor=processor,
                                                has_newsflash_in_batch=has_newsflash_in_batch,
                                            )
                                            logger.info(
                                                f"DETECTION_SIGNAL: {alert_id} ({a_type}) - "
                                                f"{city_count} cities detected. Active events: {len(store)}"
                                            )
                                            if not is_simulation:
                                                master_id = store.get(alert_id, {}).get("master_id", alert_id)
                                                persist_data = store.master_data_for_persist(master_id) or analysis
                                                await db.log_event(alert_id, a_type, "DETECTED", persist_data)
                                            relay_batch_changed = True

                                if relay_batch_changed:
                                    ws.active_events = store.active_events
                                    await _broadcast_multi_alert(ws, store, engine, push_manager, telegram_notifier)

                                memory_log_counter += 1
                                if memory_log_counter % 100 == 0 and store:
                                    store.log_memory_stats()
                            
                            await ws.broadcast({
                                "type": "health_status", 
                                "status": "OPERATIONAL" if resp.status == 200 else "DEGRADED",
                                "upstream_source": relay_upstream_label(RELAY_URL, alerts),
                                "timestamp": datetime.now(TIMEZONE).isoformat(), 
                                "version": VERSION
                            })
                    except asyncio.TimeoutError:
                        logger.warning("RELAY_TIMEOUT: Upstream relay did not respond within 5s.")
                    except aiohttp.ClientError as net_err:
                        logger.error(f"RELAY_CONNECTION_FAILURE: {net_err}")

                except Exception as e:
                    logger.error(f"RUNTIME_ERROR: {e}", exc_info=True)
            
                await asyncio.sleep(POLL_INTERVAL)
    finally:
        await telegram_notifier.close()
        await ws.stop()


async def _telegram_kfar_kama_ended(telegram_notifier, alert_id, event_data):
    if telegram_notifier and event_data:
        await telegram_notifier.notify_kfar_kama_terminated(event_data, alert_id)


async def _broadcast_multi_alert(ws, store, engine, push_manager=None, telegram_notifier=None):
    """Push the full active events array to all connected clients."""
    state_hash = store.compute_broadcast_hash()
    if store.merge_cache_valid(state_hash):
        events_list = store.get_cached_merge_payloads()
    else:
        events_list = await build_merged_payloads(
            store.active_events, engine, threshold_km=15, use_polygon_hulls=True
        )
        store.set_merge_cache(state_hash, events_list)

    await ws.broadcast({
        "type": "multi_alert",
        "events": events_list
    })

    push_events = [e for e in events_list if not e.get("is_simulation")]
    if push_manager and push_events:
        await push_manager.notify_matching_subscriptions(push_events)

    if telegram_notifier and events_list:
        active_ids = collect_active_track_ids(events_list, store.active_events)
        telegram_notifier.clear_stale_keys(active_ids)
        telegram_notifier.schedule_notify_events_if_kfar_kama(events_list)


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("SYSTEM_SHUTDOWN")
