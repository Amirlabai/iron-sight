"""
Recalculate origin_coords for archived Gaza / Lebanon missile salvos.

Unverified: calc-border ray-march via get_projected_origin.
Verified/manual: sync both coords to operator pin.
Unverified: calc-border ray-march via get_projected_origin (both fields).
"""

import argparse
import asyncio
import logging
import os
import sys

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from src.core.engine import TrackingEngine
from src.data.data_manager import LamasDataManager
from src.db.mongo_manager import MongoManager
from src.utils.trajectory_utils import set_trajectory_entry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("RecalcRegionalTrajectories")

REGIONAL_ORIGINS = {"Gaza", "Lebanon"}


def _coords_changed(a, b, eps=1e-5):
    if not a or not b or len(a) < 2 or len(b) < 2:
        return a != b
    return abs(a[0] - b[0]) > eps or abs(a[1] - b[1]) > eps


def _cities_for_origin(alert, origin):
    clusters = alert.get("clusters") or []
    matched = []
    for cl in clusters:
        if cl.get("origin") == origin:
            matched.extend(cl.get("cities") or [])
    if matched:
        return matched
    return alert.get("all_cities") or []


def _recalc_document(engine, alert):
    trajectories = alert.get("trajectories") or []
    if not trajectories:
        return False, []

    verified = bool(alert.get("verified") or alert.get("manual_origin"))
    changes = []
    doc_changed = False

    for i, traj in enumerate(trajectories):
        origin = (traj.get("origin") or "").strip()
        if origin not in REGIONAL_ORIGINS:
            continue

        old_coords = traj.get("origin_coords")

        if verified:
            marker = traj.get("marker_coords")
            if not marker or len(marker) < 2:
                continue
            new_coords = [float(marker[0]), float(marker[1])]
            mode = "verified_sync"
        else:
            cities = _cities_for_origin(alert, origin)
            if not cities:
                continue
            depth = traj.get("depth")
            if depth is None:
                depth = engine.strategic_depths.get(origin, 0.5)
            new_coords = engine.get_projected_origin(cities, origin, depth=depth)
            new_coords = [float(new_coords[0]), float(new_coords[1])]
            mode = "ray_march"

        if _coords_changed(old_coords, new_coords):
            set_trajectory_entry(traj, new_coords)
            doc_changed = True
            changes.append({
                "trajectory_index": i,
                "origin": origin,
                "old": old_coords,
                "new": new_coords,
                "mode": mode,
            })

    return doc_changed, changes


async def run(limit=None, dry_run=False):
    if not os.getenv("MONGO_URI"):
        logger.error("MONGO_URI not set (load backend/.env)")
        sys.exit(1)

    db = MongoManager()
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm, db_manager=db)

    collection = db.collections.get("missiles")
    if collection is None:
        logger.error("Missile collection not initialized")
        sys.exit(1)

    query = {"trajectories.origin": {"$in": list(REGIONAL_ORIGINS)}}
    cursor = collection.find(query).sort("_id", -1)
    if limit:
        cursor = cursor.limit(int(limit))

    stats = {"scanned": 0, "updated": 0, "unchanged": 0, "skipped": 0}

    async for doc in cursor:
        stats["scanned"] += 1
        alert_id = doc.get("id")
        if not alert_id:
            stats["skipped"] += 1
            continue

        doc.pop("_id", None)
        changed, detail = _recalc_document(engine, doc)
        if not changed:
            stats["unchanged"] += 1
            continue

        stats["updated"] += 1
        for item in detail:
            logger.info(
                f"{'[DRY-RUN] ' if dry_run else ''}{alert_id} {item['origin']}: "
                f"{item['old']} -> {item['new']}"
            )

        if not dry_run:
            await db.save_alert("missiles", doc)

    logger.info(
        f"Done. scanned={stats['scanned']} updated={stats['updated']} "
        f"unchanged={stats['unchanged']} skipped={stats['skipped']} dry_run={dry_run}"
    )


def main():
    parser = argparse.ArgumentParser(description="Recalc Gaza/Lebanon archive trajectories")
    parser.add_argument("--limit", type=int, default=None, help="Max documents to process")
    parser.add_argument("--dry-run", action="store_true", help="Log changes without writing")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
