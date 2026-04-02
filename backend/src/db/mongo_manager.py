import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from src.utils.config import MONGO_URI, DB_NAME, COLLECTION_SALVO, COLLECTION_DRONE, COLLECTION_INFILTRATION, COLLECTION_SEISMIC, COLLECTION_LOGS

logger = logging.getLogger("IronSightBackend")

class MongoManager:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
        self.db = self.client[DB_NAME] if self.client is not None else None
        
        # Initialize Collections
        self.collections = {
            "missiles": self.db[COLLECTION_SALVO] if self.db is not None else None,
            "hostileAircraftIntrusion": self.db[COLLECTION_DRONE] if self.db is not None else None,
            "terroristInfiltration": self.db[COLLECTION_INFILTRATION] if self.db is not None else None,
            "earthQuake": self.db[COLLECTION_SEISMIC] if self.db is not None else None,
        }
        self.event_logs = self.db[COLLECTION_LOGS] if self.db is not None else None

    async def save_alert(self, alert_type, payload):
        """Save a tactical alert to its respective collection."""
        collection = self.collections.get(alert_type)
        if collection is None:
            logger.warning(f"DB_SYNC_SKIPPED: Collection for {alert_type} not initialized.")
            return

        try:
            # Use update_one with upsert to avoid duplicates if same ID appears
            await collection.update_one(
                {"id": payload["id"]},
                {"$set": payload},
                upsert=True
            )
            logger.info(f"DB_SYNC_SUCCESS: {alert_type.capitalize()} {payload['id']} committed.")
        except Exception as e:
            logger.error(f"DB_SYNC_FAILURE: {e}")

    async def log_event(self, event_id, a_type, status, data=None):
        """Non-blocking lifecycle logger. Upserts event documents in event_logs."""
        if self.event_logs is None:
            return
        
        ts = datetime.now(timezone.utc).isoformat()
        timeline_entry = {"status": status, "time": ts}
        
        if data:
            timeline_entry["cities"] = len(data.get("all_cities", []))
        
        try:
            if status == "DETECTED":
                # Create new lifecycle document
                city_list = [c.get("name", c) if isinstance(c, dict) else c for c in (data or {}).get("all_cities", [])]
                doc = {
                    "event_id": event_id,
                    "category": a_type,
                    "is_simulation": (data or {}).get("is_simulation", False),
                    "start_time": ts,
                    "last_update_time": ts,
                    "end_time": None,
                    "termination_reason": None,
                    "city_count": len(city_list),
                    "city_list": city_list,
                    "updates_count": 0,
                    "timeline": [timeline_entry]
                }
                await self.event_logs.update_one(
                    {"event_id": event_id},
                    {"$set": doc},
                    upsert=True
                )
            else:
                # Append lifecycle step to existing document
                update_fields = {"last_update_time": ts}
                
                if data:
                    city_list = [c.get("name", c) if isinstance(c, dict) else c for c in data.get("all_cities", [])]
                    update_fields["city_count"] = len(city_list)
                    update_fields["city_list"] = city_list
                
                if status == "UPDATED":
                    inc_fields = {"updates_count": 1}
                else:
                    inc_fields = {}
                
                if status in ("TIMEOUT", "END_SIGNAL", "PURGED"):
                    update_fields["end_time"] = ts
                    reason = status if status != "PURGED" else None
                    if reason:
                        update_fields["termination_reason"] = reason
                        timeline_entry["reason"] = reason
                
                update_op = {"$set": update_fields, "$push": {"timeline": timeline_entry}}
                if inc_fields:
                    update_op["$inc"] = inc_fields
                
                await self.event_logs.update_one(
                    {"event_id": event_id},
                    update_op
                )
            
            logger.info(f"LOG_EVENT: {event_id} -> {status}")
        except Exception as e:
            logger.error(f"LOG_EVENT_FAILURE: {event_id} {status} - {e}")

    async def get_history(self, alert_type="missiles", limit=50):
        """Retrieve archive for a specific threat category."""
        collection = self.collections.get(alert_type)
        if collection is None: return []
        
        try:
            cursor = collection.find().sort("_id", -1).limit(limit)
            history = await cursor.to_list(length=limit)
            # Remove MongoDB _id for clean JSON serialization
            for item in history:
                item.pop("_id", None)
            return history
        except Exception as e:
            logger.error(f"DB_FETCH_FAILURE: {e}")
            return []
