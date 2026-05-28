import argparse
import asyncio
import json
import os
import sys
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from src.utils.config import (  # noqa: E402
    CITIES_DATA_FILE,
    COLLECTION_DRONE,
    COLLECTION_INFILTRATION,
    COLLECTION_SALVO,
    COLLECTION_SEISMIC,
    DB_NAME,
    MONGO_URI,
    POLYGONS_DATA_FILE,
)
from src.utils.text_utils import standardize_name  # noqa: E402


COLLECTIONS = [
    COLLECTION_SALVO,
    COLLECTION_DRONE,
    COLLECTION_INFILTRATION,
    COLLECTION_SEISMIC,
]


def load_city_id_map() -> dict[str, Any]:
    with open(CITIES_DATA_FILE, "r", encoding="utf-8") as f:
        cities_data = json.load(f)
    mapped = {}
    for city in cities_data:
        std = standardize_name(city.get("name"))
        if std:
            mapped[std] = city.get("id")
    return mapped


def load_city_polygons() -> dict[str, Any]:
    with open(POLYGONS_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def enrich_city(city: Any, city_to_id: dict[str, Any], city_polygons: dict[str, Any]) -> bool:
    if not isinstance(city, dict):
        return False
    name = city.get("name")
    std = standardize_name(name) if name else None
    city_id = city_to_id.get(std) if std else None
    boundary = city_polygons.get(str(city_id)) if city_id is not None else None

    changed = False
    if city.get("city_id") != city_id:
        city["city_id"] = city_id
        changed = True
    if city.get("boundary") != boundary:
        city["boundary"] = boundary
        changed = True
    return changed


def enrich_document(doc: dict[str, Any], city_to_id: dict[str, Any], city_polygons: dict[str, Any]) -> bool:
    changed = False
    all_cities = doc.get("all_cities")
    if isinstance(all_cities, list):
        for city in all_cities:
            if enrich_city(city, city_to_id, city_polygons):
                changed = True
    clusters = doc.get("clusters")
    if isinstance(clusters, list):
        for cluster in clusters:
            cities = cluster.get("cities") if isinstance(cluster, dict) else None
            if isinstance(cities, list):
                for city in cities:
                    if enrich_city(city, city_to_id, city_polygons):
                        changed = True
    return changed


async def run(dry_run: bool, limit: int | None) -> None:
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not configured.")

    city_to_id = load_city_id_map()
    city_polygons = load_city_polygons()
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    updated_docs = 0
    scanned_docs = 0
    try:
        for coll_name in COLLECTIONS:
            collection = db[coll_name]
            cursor = collection.find({})
            if limit is not None:
                cursor = cursor.limit(limit)

            async for doc in cursor:
                scanned_docs += 1
                if not enrich_document(doc, city_to_id, city_polygons):
                    continue

                updated_docs += 1
                if not dry_run:
                    await collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"all_cities": doc.get("all_cities", []), "clusters": doc.get("clusters", [])}},
                    )
        mode = "DRY_RUN" if dry_run else "APPLY"
        print(f"{mode}_SUMMARY scanned={scanned_docs} updated={updated_docs}")
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill city bounds into stored history alerts.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report updates without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Max docs per collection (for testing).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(dry_run=args.dry_run, limit=args.limit))
