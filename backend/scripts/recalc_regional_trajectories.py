"""
Normalize legacy missile archive rows (clusters + single trajectory + display pins).

Skips geometry rewrite on history-fixer commits unless --dedupe-verified is set
(that mode only removes extra trajectories and relabels clusters; coords unchanged).

Default: full normalize for unverified missiles matching query scope.
Non-dry-run writes require --all (safety gate). Run --dry-run --limit N first.

Runtime: one _sync_verified_history per batch; each unverified doc re-clusters and
may call get_origin + ML collapse. Use --limit for smoke tests on large DBs.
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
from src.utils.archive_normalize import (
    dedupe_verified_missile_archive,
    is_history_fixer_committed,
    normalize_missile_archive,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("RecalcRegionalTrajectories")


def _build_query(origins=None):
    query = {"trajectories.0": {"$exists": True}}
    if origins:
        query["$or"] = [
            {"trajectories.origin": o} for o in origins
        ] + [
            {"manual_origin": o} for o in origins
        ]
    return query


async def run(
    limit=None,
    dry_run=False,
    dedupe_verified=False,
    allow_strategic=True,
    confirm_all=False,
    origins=None,
):
    if not os.getenv("MONGO_URI"):
        logger.error("MONGO_URI not set (load backend/.env)")
        sys.exit(1)

    if not dry_run and not confirm_all:
        logger.error(
            "Refusing to write without --all. Run with --dry-run --limit N first, "
            "then pass --all to commit changes."
        )
        sys.exit(1)

    scope = "all missile trajectories" if not origins else f"origins={','.join(origins)}"
    logger.info(
        f"Scope: {scope} | dry_run={dry_run} dedupe_verified={dedupe_verified} "
        f"allow_strategic={allow_strategic}"
    )
    if dry_run:
        logger.info("DRY-RUN: no Mongo writes")

    db = MongoManager()
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm, db_manager=db)
    await engine._sync_verified_history()

    collection = db.collections.get("missiles")
    if collection is None:
        logger.error("Missile collection not initialized")
        sys.exit(1)

    query = _build_query(origins)
    cursor = collection.find(query).sort("_id", -1)
    if limit:
        cursor = cursor.limit(int(limit))

    stats = {
        "scanned": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "skipped_committed": 0,
        "deduped_verified": 0,
    }

    async for doc in cursor:
        stats["scanned"] += 1
        alert_id = doc.get("id")
        if not alert_id:
            stats["skipped"] += 1
            continue

        doc.pop("_id", None)
        committed = is_history_fixer_committed(doc)

        if committed:
            if not dedupe_verified:
                stats["skipped_committed"] += 1
                continue
            _alert, changed, labels = dedupe_verified_missile_archive(doc, engine=engine)
        else:
            _alert, changed, labels = await normalize_missile_archive(
                engine, doc, allow_strategic=allow_strategic
            )

        if not changed:
            stats["unchanged"] += 1
            continue

        if committed:
            stats["deduped_verified"] += 1
        stats["updated"] += 1
        logger.info(
            f"{'[DRY-RUN] ' if dry_run else ''}{alert_id}: {', '.join(labels)}"
        )

        if not dry_run:
            await db.save_alert("missiles", doc)

    logger.info(
        f"Done. scanned={stats['scanned']} updated={stats['updated']} "
        f"unchanged={stats['unchanged']} skipped={stats['skipped']} "
        f"skipped_committed={stats['skipped_committed']} "
        f"deduped_verified={stats['deduped_verified']} dry_run={dry_run}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Normalize legacy missile archive geometry (single trajectory, hulls, display pins)"
    )
    parser.add_argument("--limit", type=int, default=None, help="Max documents to process")
    parser.add_argument("--dry-run", action="store_true", help="Log changes without writing")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="confirm_all",
        help="Required for non-dry-run writes (full archive scope)",
    )
    parser.add_argument(
        "--origins",
        type=str,
        default=None,
        help="Comma-separated origin filter (e.g. Gaza,Lebanon) for partial runs",
    )
    parser.add_argument(
        "--dedupe-verified",
        action="store_true",
        help="For verified/manual rows: drop extra trajectories and relabel clusters only",
    )
    parser.add_argument(
        "--no-strategic",
        action="store_true",
        help="Do not allow Iran/Yemen origin detection during normalize",
    )
    args = parser.parse_args()
    origins = None
    if args.origins:
        origins = [o.strip() for o in args.origins.split(",") if o.strip()]
    asyncio.run(
        run(
            limit=args.limit,
            dry_run=args.dry_run,
            dedupe_verified=args.dedupe_verified,
            allow_strategic=not args.no_strategic,
            confirm_all=args.confirm_all,
            origins=origins,
        )
    )


if __name__ == "__main__":
    main()
