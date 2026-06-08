"""
Delete archive rows whose `time` field is in year 2000 (restore_history_dates fallback).

Usage:
  .venv\\Scripts\\python.exe research_scripts/delete_year_2000_records.py --dry-run
  .venv\\Scripts\\python.exe research_scripts/delete_year_2000_records.py --delete
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from src.utils.config import (
    COLLECTION_DRONE,
    COLLECTION_INFILTRATION,
    COLLECTION_NEWSFLASH,
    COLLECTION_SALVO,
    COLLECTION_SEISMIC,
    DB_NAME,
)

YEAR_2000_TIME = {"$regex": r"^2000-"}

COLLECTIONS = [
    ("missiles", COLLECTION_SALVO),
    ("hostileAircraftIntrusion", COLLECTION_DRONE),
    ("terroristInfiltration", COLLECTION_INFILTRATION),
    ("earthQuake", COLLECTION_SEISMIC),
    ("newsFlash", COLLECTION_NEWSFLASH),
]


async def main(dry_run: bool):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    uri = os.getenv("MONGO_URI")
    if not uri:
        print("MONGO_URI not set in backend/.env")
        return 1

    client = AsyncIOMotorClient(uri)
    db = client[DB_NAME]

    total = 0
    for label, coll_name in COLLECTIONS:
        coll = db[coll_name]
        count = await coll.count_documents({"time": YEAR_2000_TIME})
        if count == 0:
            continue
        print(f"{label} ({coll_name}): {count} records with time ^2000-")
        sample = await coll.find({"time": YEAR_2000_TIME}, {"id": 1, "time": 1, "title": 1}).limit(5).to_list(5)
        for doc in sample:
            print(f"  id={doc.get('id')} time={doc.get('time')} title={doc.get('title')}")
        if count > 5:
            print(f"  ... and {count - 5} more")
        total += count
        if not dry_run:
            result = await coll.delete_many({"time": YEAR_2000_TIME})
            print(f"  deleted {result.deleted_count}")

    if total == 0:
        print("No year-2000 time records found.")
        return 0

    print(f"\nTotal matched: {total}")
    if dry_run:
        print("Dry run — no deletes. Re-run with --delete to remove.")
    else:
        print("Delete complete.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Count only (default)")
    parser.add_argument("--delete", action="store_true", help="Delete matched records")
    args = parser.parse_args()
    dry = not args.delete
    raise SystemExit(asyncio.run(main(dry)))
