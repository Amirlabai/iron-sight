import logging
from motor.motor_asyncio import AsyncIOMotorClient
from src.utils.config import MONGO_URI, DB_NAME, COLLECTION_SALVO, COLLECTION_DRONE, COLLECTION_INFILTRATION, COLLECTION_SEISMIC

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
