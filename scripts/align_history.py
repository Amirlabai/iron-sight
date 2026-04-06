import asyncio
import os
import sys
import json
import logging

# Add project root and backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "backend"))

from src.db.mongo_manager import MongoManager
from src.data.data_manager import LamasDataManager
from src.core.engine import TrackingEngine

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("HistoryAligner")

async def align_history():
    logger.info("IRON SIGHT: Starting History Alignment Operation...")
    
    db = MongoManager()
    dm = LamasDataManager()
    
    try:
        await dm.load()
        engine = TrackingEngine(dm)
    except Exception as e:
        logger.error(f"INITIALIZATION_FAILED: {e}")
        return

    total_stats = {"processed": 0, "corrected": 0, "skipped": 0}

    # Only process tactical threats that have trajectories
    categories = ["missiles", "hostileAircraftIntrusion"]
    
    for category in categories:
        logger.info(f"Processing category: {category}")
        # Fetch a larger batch for bulk alignment
        history = await db.get_history(alert_type=category, limit=5000)
        
        for alert in history:
            alert_id = alert.get("id")
            if not alert_id: continue
            
            total_stats["processed"] += 1
            
            if alert.get("verified"):
                total_stats["skipped"] += 1
                continue
                
            cities = alert.get("all_cities", [])
            if not cities:
                continue
            
            # Extract current origin
            trajectories = alert.get("trajectories", [])
            current_origin = trajectories[0].get("origin", "Unknown") if trajectories else "Unknown"
            
            # Re-guess origin using updated engine logic
            new_origin, depth = await engine.get_origin(cities)
            
            if new_origin != current_origin:
                logger.info(f"[*] CORRECTION [{alert_id}]: {current_origin} -> {new_origin}")
                
                # Calculate new projection
                new_coords = engine.get_projected_origin(cities, new_origin, depth=depth)
                
                # Commit to DB (mark as unverified since it's an automated guess)
                success = await db.update_alert_origin(
                    category, 
                    alert_id, 
                    new_origin, 
                    new_coords, 
                    verified=False
                )
                if success:
                    total_stats["corrected"] += 1
            
    logger.info(f"OPERATION_COMPLETE")
    logger.info(f"Total Processed: {total_stats['processed']}")
    logger.info(f"Total Corrected: {total_stats['corrected']}")
    logger.info(f"Total Skipped (Verified): {total_stats['skipped']}")

if __name__ == "__main__":
    if not os.getenv("MONGO_URI"):
        logger.error("ENVIRONMENT_ERROR: MONGO_URI not set.")
        sys.exit(1)
    asyncio.run(align_history())
