import asyncio
import os
import sys
import logging
from datetime import datetime

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("HistoryRestorer")

async def restore_dates():
    logger.info("IRON SIGHT: Starting History Date Restoration Operation...")
    
    db = MongoManager()
    categories = ["missiles", "hostileAircraftIntrusion", "terroristInfiltration", "earthQuake"]
    
    stats = {"processed": 0, "restored": 0, "skipped": 0, "fallbacked": 0}

    for cat in categories:
        logger.info(f"Processing category: {cat}")
        # Fetch all records for this category
        history = await db.get_history(alert_type=cat, limit=10000)
        
        for alert in history:
            alert_id = str(alert.get('id'))
            if not alert_id: continue
            
            stats["processed"] += 1
            
            current_time = alert.get("time", "")
            # Check if it's already ISO (has 'T' or ' ')
            if "T" in current_time or (len(current_time) > 8 and " " in current_time):
                stats["skipped"] += 1
                continue
            
            # Lookup in event_logs
            log = await db.db["event_logs"].find_one({"event_id": alert_id})
            if log and log.get("start_time"):
                new_time = log["start_time"]
            else:
                # FALLBACK: Set to very early date to resolve future filtering issues
                # Prepend 2000-01-01 to existing HH:MM:SS (or 00:00:00 if empty)
                time_part = current_time if len(current_time) == 8 else "00:00:00"
                new_time = f"2000-01-01T{time_part}"
                stats["fallbacked"] += 1
                
            # Get the specific collection object from MongoManager
            collection = db.collections.get(cat)
            if collection is None:
                logger.warning(f"Collection for {cat} not found, skipping...")
                continue
            
            result = await collection.update_one(
                {"id": alert.get("id")}, 
                {"$set": {"time": new_time}}
            )
            
            if result.modified_count > 0:
                stats["restored"] += 1
                if stats["restored"] % 50 == 0:
                    logger.info(f"Progress: {stats['restored']} records updated...")

    logger.info(f"OPERATION_COMPLETE")
    logger.info(f"Total Processed: {stats['processed']}")
    logger.info(f"Total Restored: {stats['restored']}")
    logger.info(f"Total Fallbacked (2000-01-01): {stats['fallbacked']}")
    logger.info(f"Total Skipped (Already ISO): {stats['skipped']}")

if __name__ == "__main__":
    if not os.getenv("MONGO_URI"):
        # Attempt to load from .env if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
            
    if not os.getenv("MONGO_URI"):
        logger.error("ENVIRONMENT_ERROR: MONGO_URI not set.")
        sys.exit(1)
        
    asyncio.run(restore_dates())
