import asyncio
import os
import sys

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager

async def audit_logs_fast():
    db = MongoManager()
    categories = ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]
    
    for cat in categories:
        history = await db.get_history(alert_type=cat, limit=1000)
        ids = [str(a.get('id')) for a in history if a.get('id')]
        if not ids:
            print(f"Category: {cat:<25} | No data found.")
            continue
            
        # Bulk find in event_logs
        logs = await db.db["event_logs"].find({"event_id": {"$in": ids}}).to_list(None)
        found_ids = {l['event_id'] for l in logs}
        
        total = len(ids)
        found = len(found_ids)
        
        print(f"Category: {cat:<25} | Total: {total:<5} | Logs Found: {found:<5}")

if __name__ == "__main__":
    asyncio.run(audit_logs_fast())
