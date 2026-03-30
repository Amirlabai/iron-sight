import json
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def migrate():
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "iron_sight_db")
    coll_name = os.getenv("COLLECTION_NAME", "salvo_history")
    history_file = "history.json"

    if not mongo_uri:
        print("Error: MONGO_URI not found in .env")
        return

    if not os.path.exists(history_file):
        print(f"Error: {history_file} not found.")
        return

    print(f"Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    collection = db[coll_name]

    with open(history_file, 'r', encoding='utf-8') as f:
        history_data = json.load(f)

    print(f"Found {len(history_data)} salvos in local archive. Uploading...")

    count = 0
    for salvo in history_data:
        try:
            # Upsert to avoid duplicates
            await collection.update_one(
                {"id": salvo["id"]},
                {"$set": salvo},
                upsert=True
            )
            count += 1
        except Exception as e:
            print(f"Failed to upload salvo {salvo.get('id')}: {e}")

    print(f"Mission Accomplished: {count} salvos synchronized with the cloud.")

if __name__ == "__main__":
    asyncio.run(migrate())
