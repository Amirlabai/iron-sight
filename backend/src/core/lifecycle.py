"""Active-event lifecycle: timeout, persist, purge."""

import logging

from src.utils.cluster_utils import group_events, merge_event_group

logger = logging.getLogger("IronSightTerminal")

INACTIVITY_TIMEOUT = 1200  # 20 minutes of silence


async def end_event(
    store, eid, now, db, telegram_notifier, *,
    lifecycle_status=None, log_status="END_SIGNAL", log_message=None, skip_db_log=False,
):
    """Mark stub ended, log lifecycle, notify telegram."""
    fields = {"end_time": now}
    if lifecycle_status is not None:
        fields["lifecycle_status"] = lifecycle_status
    store.set_fields(eid, **fields)
    ev = store.get(eid, {})
    if log_message:
        logger.info(log_message)
    if ev and not skip_db_log and not ev.get("data", {}).get("is_simulation"):
        await db.log_event(eid, ev["category"], log_status, ev["data"])
    if ev and telegram_notifier:
        await telegram_notifier.notify_kfar_kama_terminated(ev["data"], eid)


async def maintain_lifecycle(store, engine, db, ws, telegram_notifier, now, broadcast_fn):
    """
    Run inactivity timeout, cluster persist, and purge.
    Returns True if any events were purged.
    """
    active_events = store.active_events
    all_groups = group_events(active_events, include_all=True)
    purged_ids = []

    for group_ids in all_groups:
        members = [active_events[gid] for gid in group_ids if gid in active_events]
        if not members:
            continue

        timed_out = False
        for gid in group_ids:
            ev = active_events[gid]
            if ev["end_time"] is None and (now - ev["last_update_time"] > INACTIVITY_TIMEOUT):
                store.set_field(gid, "end_time", now)
                if ev.get("category") == "newsFlash" and not ev.get("lifecycle_status"):
                    store.set_field(gid, "lifecycle_status", "ended")
                timed_out = True
                ev = store.get(gid, {})
                logger.info(f"EVENT_TIMEOUT: {gid} - Silence depth exceeded. Marking for termination.")
                if not ev.get("data", {}).get("is_simulation"):
                    await db.log_event(gid, ev["category"], "TIMEOUT", ev["data"])
                if telegram_notifier:
                    await telegram_notifier.notify_kfar_kama_terminated(ev["data"], gid)

        if timed_out:
            active_events = store.active_events
            members = [active_events[gid] for gid in group_ids if gid in active_events]

        all_ended = all(m["end_time"] is not None for m in members)
        any_expired = any(m["end_time"] and (now - m["end_time"] > 10) for m in members)

        if not (all_ended and any_expired):
            continue

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
                history = await db.get_consolidated_history(limit=50, slim=True)
                await ws.broadcast({"type": "history_sync", "data": history})
            except Exception as db_err:
                logger.error(f"CLUSTER_PERSIST_FAILURE: {master_payload['id']} - {db_err}")
        elif not has_persistent:
            try:
                history = await db.get_consolidated_history(limit=50, slim=True)
                await ws.broadcast({"type": "history_sync", "data": history})
            except Exception as db_err:
                logger.error(f"NEWSFLASH_HISTORY_SYNC_FAILURE: {db_err}")

        active_events = store.active_events
        for gid in group_ids:
            if gid not in active_events:
                continue
            purge_ev = active_events[gid]
            category = purge_ev["category"]
            city_count = len(purge_ev["data"].get("all_cities", []))
            if not purge_ev["data"].get("is_simulation"):
                await db.log_event(gid, category, "PURGED", purge_ev["data"])
            if telegram_notifier:
                await telegram_notifier.notify_kfar_kama_terminated(purge_ev["data"], gid)
            store.pop(gid)
            purged_ids.append(gid)
            logger.info(f"EVENT_PURGED: {gid} ({category}, {city_count} cities)")

    if purged_ids:
        ws.active_events = store.active_events
        await broadcast_fn()
        if not store:
            await ws.broadcast({"type": "reset"})
        return True
    return False
