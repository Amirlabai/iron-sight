import asyncio
import aiohttp
import json
import logging
import os
import sys
import time
from datetime import datetime

from src.utils.config import (
    POLL_INTERVAL, RELAY_URL, RELAY_AUTH_KEY, TIMEZONE, VAPID_CLAIMS_EMAIL,
    LOG_LEVEL, POLL_HEARTBEAT_EVERY, WS_PORT,
)
from src.db.mongo_manager import MongoManager
from src.data.data_manager import LamasDataManager
from src.core.engine import TrackingEngine
from src.core.event_store import EventStore
from src.core.threat_processor import ThreatProcessor
from src.core.lifecycle import maintain_lifecycle
from src.core.relay_ingest import ingest_relay_batch
from src.api.ws_manager import WebSocketManager
from src.services.push_manager import PushManager
from src.services.telegram_notifier import TelegramNotifier
from src.utils.kfar_kama import collect_active_track_ids
from src.utils.cluster_utils import build_merged_payloads
from src.utils.outbound_policy import relay_upstream_label
from src.utils.observability import (
    estimate_json_bytes,
    log_broadcast,
    log_relay_poll,
    log_runtime_banner,
    rss_suffix,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
)
logger = logging.getLogger("IronSightTerminal")

VERSION = "0.0.0"
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "..", "version.json"), "r") as f:
        vdata = json.load(f)
        VERSION = vdata.get("version", "0.0.0")
except Exception as e:
    logger.warning(f"VERSION_INIT_FAILURE: {e}")


async def main():
    logger.info(f"IRON SIGHT TACTICAL OPERATING SYSTEM (v{VERSION}) - INITIALIZING")
    if VAPID_CLAIMS_EMAIL == "mailto:ops@iron-sight.local":
        logger.warning("VAPID_CLAIMS_EMAIL is default placeholder — set a real contact in production.")

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
    log_runtime_banner(
        version=VERSION,
        relay_enabled=bool(RELAY_URL),
        port=WS_PORT,
        python_version=sys.version.split()[0],
    )

    store = EventStore()
    poll_counter = 0

    async def broadcast_active():
        ws.active_events = store.active_events
        await _broadcast_multi_alert(ws, store, engine, push_manager, telegram_notifier)

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "IronSight/0.0.0"}) as session:
            while True:
                try:
                    now = time.time()
                    purged = await maintain_lifecycle(
                        store, engine, db, ws, telegram_notifier, now, broadcast_active
                    )
                    if purged:
                        stats = store.memory_stats()
                        logger.info(
                            f"LIFECYCLE_PURGE: active={stats['members']} "
                            f"masters={stats['masters']}{rss_suffix()}"
                        )

                    if not RELAY_URL:
                        poll_counter += 1
                        if poll_counter % POLL_HEARTBEAT_EVERY == 0:
                            stats = store.memory_stats()
                            logger.info(
                                f"POLL_HEARTBEAT: relay=disabled active={stats['members']} "
                                f"ws_clients={len(ws.clients)}{rss_suffix()}"
                            )
                        await asyncio.sleep(POLL_INTERVAL)
                        continue

                    try:
                        async with session.get(
                            RELAY_URL,
                            headers={"x-relay-auth": RELAY_AUTH_KEY},
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as resp:
                            alerts = []
                            if resp.status == 200:
                                data = json.loads(await resp.text())
                                alerts = data if isinstance(data, list) else [data] if data else []

                                changed = await ingest_relay_batch(
                                    store, alerts, dm, processor, db, telegram_notifier, now
                                )
                                poll_counter += 1
                                stats = store.memory_stats()
                                if changed or poll_counter % POLL_HEARTBEAT_EVERY == 0:
                                    log_relay_poll(
                                        alert_count=len(alerts),
                                        changed=changed,
                                        store_members=stats["members"],
                                        store_masters=stats["masters"],
                                        unique_cities=stats["unique_cities"],
                                    )
                                if changed:
                                    await broadcast_active()
                            else:
                                poll_counter += 1
                                logger.warning(
                                    f"RELAY_DEGRADED: status={resp.status}{rss_suffix()}"
                                )

                            await ws.broadcast({
                                "type": "health_status",
                                "status": "OPERATIONAL" if resp.status == 200 else "DEGRADED",
                                "upstream_source": relay_upstream_label(RELAY_URL, alerts),
                                "timestamp": datetime.now(TIMEZONE).isoformat(),
                                "version": VERSION,
                            })
                    except asyncio.TimeoutError:
                        poll_counter += 1
                        logger.warning(f"RELAY_TIMEOUT: upstream did not respond within 5s{rss_suffix()}")
                    except aiohttp.ClientError as net_err:
                        poll_counter += 1
                        logger.error(f"RELAY_CONNECTION_FAILURE: {net_err}{rss_suffix()}")

                except Exception as e:
                    logger.error(f"RUNTIME_ERROR: {e}{rss_suffix()}", exc_info=True)

                await asyncio.sleep(POLL_INTERVAL)
    finally:
        await telegram_notifier.close()
        await ws.stop()


async def _broadcast_multi_alert(ws, store, engine, push_manager=None, telegram_notifier=None):
    """Push the full active events array to all connected clients."""
    state_hash = store.compute_broadcast_hash()
    cache_hit = store.merge_cache_valid(state_hash)
    if cache_hit:
        events_list = store.get_cached_merge_payloads()
    else:
        events_list = await build_merged_payloads(
            store.active_events, engine, threshold_km=15, use_polygon_hulls=True
        )
        store.set_merge_cache(state_hash, events_list)

    payload = {"type": "multi_alert", "events": events_list}
    log_broadcast(
        event_count=len(events_list),
        cache_hit=cache_hit,
        payload_bytes=estimate_json_bytes(payload),
    )

    await ws.broadcast(payload)

    push_events = [e for e in events_list if not e.get("is_simulation")]
    if push_manager and push_events:
        await push_manager.notify_matching_subscriptions(push_events)

    if telegram_notifier and events_list:
        active_ids = collect_active_track_ids(events_list, store.active_events)
        telegram_notifier.clear_stale_keys(active_ids)
        telegram_notifier.schedule_notify_events_if_kfar_kama(events_list)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SYSTEM_SHUTDOWN")
