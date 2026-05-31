"""
Find and optionally delete the latest Iran-tagged salvo for טבריה + מצפה + כפר חיטים.
Usage:
  .venv\\Scripts\\python.exe research_scripts/delete_galilee_iran_salvo.py --dry-run
  .venv\\Scripts\\python.exe research_scripts/delete_galilee_iran_salvo.py --delete
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

GALILEE_CITIES = {"טבריה", "כפר חיטים", "מצפה"}


async def main(dry_run: bool, do_delete: bool):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "iron_sight_db")
    coll_name = os.getenv("COLLECTION_NAME", "salvo_history")

    if not uri:
        print("MONGO_URI not set — skip remote delete; use history-fixer SPLIT on production.")
        return 1

    client = AsyncIOMotorClient(uri)
    coll = client[db_name][coll_name]

    cursor = coll.find({
        "trajectories.origin": {"$in": ["Iran", "North Iran"]},
        "all_cities.name": {"$all": list(GALILEE_CITIES)},
    }).sort("id", -1).limit(5)

    matches = await cursor.to_list(length=5)
    if not matches:
        print("No Iran salvo found for Galilee city triple.")
        return 0

    for doc in matches:
        sid = doc.get("id")
        origin = (doc.get("trajectories") or [{}])[0].get("origin")
        names = [c.get("name") for c in doc.get("all_cities", [])]
        print(f"Match id={sid} origin={origin} cities={names}")

    target = matches[0]
    target_id = target.get("id")
    print(f"\nLatest match: {target_id}")

    if dry_run or not do_delete:
        print("Dry run — no delete performed.")
        return 0

    result = await coll.delete_one({"id": target_id})
    if result.deleted_count:
        print(f"Deleted salvo {target_id}")
        return 0
    print(f"Delete failed for {target_id}")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    dry = not args.delete
    raise SystemExit(asyncio.run(main(dry, args.delete)))
