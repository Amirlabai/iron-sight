import json
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def extract_all_iran_clusters():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "iron_sight")
    coll_name = os.getenv("COLLECTION_NAME", "salvo_history")

    if not mongo_uri:
        print("MONGO_URI not found in .env")
        return

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    collection = db[coll_name]

    # Query: Match any salvo that has a cluster from Iran or North Iran
    cursor = collection.find({
        "$or": [
            {"clusters.origin": "Iran"},
            {"clusters.origin": "North Iran"}
        ]
    }).sort("_id", -1)
    
    items = await cursor.to_list(length=1000) # Fetch up to 1000 salvos

    if not items:
        print("No Iranian clusters found in history.")
        return

    print("### Comprehensive Iranian Cluster Audit")
    print("| Date | Time | Salvo ID | Cluster # | Origin | Cities | Major Targets |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    unique_salvos = set()
    total_iran_clusters = 0
    
    for salvo in items:
        sid = salvo.get("id", "N/A")
        date = salvo.get("date", "N/A")
        time_str = salvo.get("time", "N/A")
        
        clusters = salvo.get("clusters", [])
        for i, cluster in enumerate(clusters):
            origin = cluster.get("origin", "Unknown")
            if origin in ["Iran", "North Iran"]:
                total_iran_clusters += 1
                unique_salvos.add(sid)
                
                cities = cluster.get("cities", [])
                city_count = len(cities)
                
                city_names = [c.get("name", "Unknown") for c in cities[:3]]
                snippet = ", ".join(city_names)
                if len(cities) > 3:
                    snippet += "..."
                    
                print(f"| {date} | {time_str} | {sid} | {i} | {origin} | {city_count} | {snippet} |")

    print(f"\n**Audit Summary**: Found {total_iran_clusters} Iranian clusters across {len(unique_salvos)} unique salvos.")

if __name__ == "__main__":
    asyncio.run(extract_all_iran_clusters())
