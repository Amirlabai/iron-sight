import asyncio
from src.db.mongo_manager import MongoManager
from datetime import datetime, timezone

async def check():
    db = MongoManager()
    print("Checking 'missiles' collection...")
    cursor = db.collections['missiles'].find().sort("_id", -1).limit(5)
    docs = await cursor.to_list(length=5)
    for d in docs:
        print(f"ID: {d.get('id')}, Time: {d.get('time')}")
    
    if docs:
        sample_time = docs[0].get('time')
        print(f"Sample time: {sample_time}")
        print(f"ISO Format from Python: {datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    asyncio.run(check())
