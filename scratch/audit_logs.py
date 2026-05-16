import asyncio
import os
import sys

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager

async def audit_logs():
    db = MongoManager()
    categories = ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]
    
    for cat in categories:
        history = await db.get_history(alert_type=cat, limit=1000)
        total = len(history)
        found = 0
        for alert in history:
            alert_id = str(alert.get('id'))
            log = await db.db["event_logs"].find_one({"event_id": alert_id})
            if log:
                found += 1
        
        print(f"Category: {cat:<25} | Total: {total:<5} | Logs Found: {found:<5}")

if __name__ == "__main__":
    asyncio.run(audit_logs())
