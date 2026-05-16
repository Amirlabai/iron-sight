import asyncio
import os
import sys
from datetime import datetime

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager

async def check_ids():
    db = MongoManager()
    categories = ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]
    
    print(f"{'Category':<25} | {'ID':<20} | {'Time String'}")
    print("-" * 65)
    
    for cat in categories:
        history = await db.get_history(alert_type=cat, limit=5)
        for alert in history:
            print(f"{cat:<25} | {str(alert.get('id')):<20} | {alert.get('time')}")

if __name__ == "__main__":
    asyncio.run(check_ids())
