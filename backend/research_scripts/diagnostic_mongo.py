import motor.motor_asyncio
import os
import asyncio
import json
from dotenv import load_dotenv

async def run():
    load_dotenv()
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "iron_sight")
    coll_name = os.getenv("COLLECTION_NAME", "salvo_history")
    
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client[db_name]
    coll = db[coll_name]
    
    ids_to_check = ["134195115600000000", "134194511180000000", "134194480900000000"]
    for sid in ids_to_check:
        print(f"\n--- Checking ID: {sid} ---")
        doc = await coll.find_one({"id": sid})
        if doc:
            # Print structure details
            print(f"Salvo ID: {doc.get('id')}")
            print(f"Title: {doc.get('title')}")
            all_cities = doc.get("all_cities", [])
            print(f"all_cities count: {len(all_cities)}")
            
            clusters = doc.get("clusters", [])
            print(f"clusters count: {len(clusters)}")
            for i, cl in enumerate(clusters):
                cities_in_cl = cl.get("cities", [])
                print(f"  Cluster {i} origin: {cl.get('origin')}")
                print(f"  Cluster {i} cities count: {len(cities_in_cl)}")
        else:
            print("Document not found.")

if __name__ == "__main__":
    asyncio.run(run())
