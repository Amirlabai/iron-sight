import json
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def extract_iran_clusters_fixed():
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

    # Query: Look for Iran OR North Iran (the strategic alias)
    # Both are Iranian territories in the engine
    cursor = collection.find({
        "$or": [
            {"highlight_origins.name": "Iran"},
            {"clusters.origin": "Iran"},
            {"clusters.origin": "North Iran"}
        ]
    }).sort("_id", -1)
    
    items = await cursor.to_list(length=200)

    if not items:
        print("No Iran/North Iran alerts found.")
        return

    print("### Iran Alert History (FIXED PARSING)")
    print("| Date | Time | Salvo ID | Cluster Index | Strategic Origin | City Count | Major Cities | Status |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for salvo in items:
        sid = salvo.get("id", "N/A")
        date = salvo.get("date", "N/A")
        time_str = salvo.get("time", "N/A")
        
        clusters = salvo.get("clusters", [])
        for i, cluster in enumerate(clusters):
            origin = cluster.get("origin", "Unknown")
            
            # Map North Iran to Iran for the user table
            is_iran = origin in ["Iran", "North Iran"]
            if not is_iran: continue
            
            cities = cluster.get("cities", [])
            city_count = len(cities)
            
            city_names = [c.get("name", "Unknown") for c in cities[:3]]
            snippet = ", ".join(city_names)
            if len(cities) > 3:
                snippet += "..."
                
            status = "**SKIP**" if city_count < 10 else "**KEEP**"
            print(f"| {date} | {time_str} | {sid} | {i} | {origin} | {city_count} | {snippet} | {status} |")

if __name__ == "__main__":
    asyncio.run(extract_iran_clusters_fixed())
