"""Relay batch ingest: clearance signals and threat detections."""

import logging
from datetime import datetime

from src.core.lifecycle import end_event
from src.utils.config import TIMEZONE

logger = logging.getLogger("IronSightTerminal")

# Pikud HaOref may emit a newsFlash clearance without alert_id; end all live events.
CLEARANCE_BROADCAST_ALL_WHEN_UNKNOWN_ID = True


async def ingest_relay_batch(store, alerts, dm, processor, db, telegram_notifier, now):
    """
    Process one relay poll batch.
    Returns True if client-visible state changed.
    """
    has_newsflash_in_batch = any(
        a.get("type") == "newsFlash" and (a.get("data") or a.get("cities"))
        for a in alerts
    )
    changed = False
    active_events = store.active_events

    for alert_payload in alerts:
        a_type = str(alert_payload.get("type", ""))
        instructions = str(alert_payload.get("instructions", ""))
        alert_id = alert_payload.get("id")

        is_warning = a_type == "newsFlash" and (alert_payload.get("data") or alert_payload.get("cities"))
        is_clearance = "האירוע הסתיים" in instructions or (a_type == "newsFlash" and not is_warning)

        if is_clearance:
            if await _handle_clearance(
                store, dm, db, telegram_notifier, now, alert_id, instructions, active_events
            ):
                changed = True
            active_events = store.active_events
            continue

        if a_type not in ("missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake", "newsFlash"):
            continue
        if not alert_id:
            continue

        cities_raw = alert_payload.get("data") or alert_payload.get("cities", [])
        if isinstance(cities_raw, str):
            cities_raw = [cities_raw]
        if not cities_raw:
            logger.warning(f"EMPTY_PAYLOAD: {alert_id} ({a_type}) - No city data in payload.")
            continue

        is_simulation = alert_payload.get("is_simulation", False)
        allow_strategic = has_newsflash_in_batch or store.has_active_newsflash()
        analysis = await processor.process(
            a_type,
            cities_raw,
            active_events=None,
            has_newsflash_in_batch=allow_strategic,
            use_polygon_hulls=False,
        )
        if not analysis:
            continue

        if a_type == "missiles":
            if await _supersede_newsflash(store, analysis, alert_id, is_simulation, db, telegram_notifier, now):
                changed = True

        event_time = (
            alert_payload.get("alertDate", "").replace(" ", "T")
            or datetime.now(TIMEZONE).isoformat()
        )

        if alert_id in store:
            upd_changed, new_count, total_cities = await store.apply_rolling_update(
                alert_id,
                analysis,
                a_type,
                is_simulation,
                event_time,
                now,
                processor,
                allow_strategic,
            )
            if upd_changed:
                master_id = store.get(alert_id, {}).get("master_id", alert_id)
                full_analysis = store.master_data_for_persist(master_id)
                logger.info(
                    f"ROLLING_UPDATE: {alert_id} ({a_type}) - +{new_count} new cities. Total: {total_cities}"
                )
                if not is_simulation and full_analysis:
                    await db.log_event(alert_id, a_type, "UPDATED", full_analysis)
                changed = True
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
                has_newsflash_in_batch=allow_strategic,
            )
            logger.info(
                f"DETECTION_SIGNAL: {alert_id} ({a_type}) - "
                f"{city_count} cities detected. Active events: {len(store)}"
            )
            if not is_simulation:
                master_id = store.get(alert_id, {}).get("master_id", alert_id)
                persist_data = store.master_data_for_persist(master_id) or analysis
                await db.log_event(alert_id, a_type, "DETECTED", persist_data)
            changed = True

    return changed


async def _handle_clearance(store, dm, db, telegram_notifier, now, alert_id, instructions, active_events):
    target_ended_cities = []
    for area, cities_dict in dm.areas.items():
        if area in instructions:
            target_ended_cities.extend(cities_dict.keys())
    for city in dm.city_map.keys():
        if city in instructions:
            target_ended_cities.append(city)

    ended_ids = []
    if target_ended_cities:
        target_set = set(target_ended_cities)
        for eid, ev in active_events.items():
            if ev["end_time"] is None:
                ev_cities = {c["name"] for c in ev["data"].get("all_cities", [])}
                if ev_cities and ev_cities.issubset(target_set):
                    ended_ids.append(eid)

        for eid in ended_ids:
            await end_event(
                store, eid, now, db, telegram_notifier,
                lifecycle_status="cleared",
                log_message=f"GRANULAR_END_SIGNAL: {eid} terminated based on region match in newsFlash.",
            )
        return bool(ended_ids)

    if alert_id and alert_id in store:
        await end_event(
            store, alert_id, now, db, telegram_notifier,
            lifecycle_status="cleared",
            log_message=f"END_SIGNAL_RECEIVED: {alert_id}",
        )
        return True

    if (alert_id is None or alert_id not in store) and CLEARANCE_BROADCAST_ALL_WHEN_UNKNOWN_ID:
        for eid, ev in list(store.items()):
            if ev["end_time"] is None:
                await end_event(store, eid, now, db, telegram_notifier, lifecycle_status="cleared")
        if store:
            logger.info(f"END_SIGNAL_BROADCAST: All {len(store)} active events marked for termination.")
        return True

    return False


async def _supersede_newsflash(store, analysis, alert_id, is_simulation, db, telegram_notifier, now):
    incoming_cities = {c["name"] for c in analysis.get("all_cities", [])}
    changed = False
    for gid, gv in list(store.items()):
        if gv["category"] == "newsFlash" and gv["end_time"] is None:
            gv_cities = {c["name"] for c in gv["data"].get("all_cities", [])}
            if gv_cities.intersection(incoming_cities):
                skip_db_log = gv["data"].get("is_simulation") or is_simulation
                await end_event(
                    store, gid, now, db, telegram_notifier,
                    lifecycle_status="superseded",
                    log_status="SUPERSEDED",
                    skip_db_log=skip_db_log,
                    log_message=f"NEWSFLASH_SUPERSEDED: {gid} terminated by incoming missile alert {alert_id}",
                )
                changed = True
    return changed
