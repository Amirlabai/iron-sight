import asyncio
import os
import sys
from datetime import datetime

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager

async def check_logs():
    db = MongoManager()
    
    # Get some IDs from missiles
    history = await db.get_history(alert_type="missiles", limit=10)
    
    print(f"{'ID':<20} | {'Log Time'}")
    print("-" * 40)
    
    for alert in history:
        alert_id = str(alert.get('id'))
        # Check event_logs collection
        log = await db.db["event_logs"].find_one({"event_id": alert_id})
        if log:
            print(f"{alert_id:<20} | {log.get('start_time')}")
        else:
            print(f"{alert_id:<20} | NO LOG FOUND")

if __name__ == "__main__":
    asyncio.run(check_logs())
