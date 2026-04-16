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
            # v0.9.0: Ensure verified flag is preserved if not explicitly overwritten
            if "verified" not in payload:
                existing = await collection.find_one({"id": payload["id"]})
                if existing and existing.get("verified"):
                    payload["verified"] = True

            await collection.update_one(
                {"id": payload["id"]},
                {"$set": payload},
                upsert=True
            )
            
            merged_info = f" (Unified {len(payload['merged_ids'])} IDs)" if "merged_ids" in payload else ""
            logger.info(f"DB_SYNC_SUCCESS: {alert_type.capitalize()} {payload['id']} committed.{merged_info}")
        except Exception as e:
            logger.error(f"DB_SYNC_FAILURE: {e}")

    async def update_alert_origin(self, alert_type, alert_id, origin_name, origin_coords, verified=True):
        """Update the origin of an existing alert and mark as verified."""
        collection = self.collections.get(alert_type)
        if collection is None: return False
        
        try:
            # Update the main trajectories and origin metadata
            update_data = {
                "verified": verified,
                "trajectories.0.origin": origin_name,
                "trajectories.0.marker_coords": origin_coords,
                # Also update clusters if it's a unified one
                "clusters.0.origin": origin_name
            }
            
            result = await collection.update_one(
                {"id": alert_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"DB_UPDATE_FAILURE: {alert_id} - {e}")
            return False

    async def split_alert(self, alert_type, alert_id):
        """EXPERIMENTAL: Remove a merged alert. (Actual splitting logic handled by re-processor)."""
        collection = self.collections.get(alert_type)
        if collection is None: return False
        try:
            result = await collection.delete_one({"id": alert_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"DB_DELETE_FAILURE: {alert_id} - {e}")
            return False

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
            logger.error(f"DB_FETCH_FAILURE for {alert_type}: {e}")
            return []

    async def get_alert(self, alert_id, alert_type="missiles"):
        """Retrieve a single alert from the database by ID."""
        collection = self.collections.get(alert_type)
        if collection is None: return None
        try:
            doc = await collection.find_one({"id": alert_id})
            if doc: doc.pop("_id", None)
            return doc
        except Exception as e:
            logger.error(f"DB_FETCH_FAILURE for alert {alert_id}: {e}")
            return None

    async def get_consolidated_history(self, limit=50):
        """Retrieve archive across all tactical categories, unified and sorted."""
        import asyncio
        try:
            # Parallel fetch from all collections
            tasks = [self.get_history(alert_type, limit=limit) for alert_type in self.collections]
            results = await asyncio.gather(*tasks)
            
            # Combine all results
            unified = []
            for res in results:
                unified.extend(res)
            
            # Sort by ID descending (Pikud HaOref IDs are chronological strings)
            # Ensure consistent sorting across all categories
            unified.sort(key=lambda x: str(x.get("id", "")), reverse=True)
            
            return unified[:limit]
        except Exception as e:
            logger.error(f"DB_CONSOLIDATED_FETCH_FAILURE: {e}")
            return []

    async def get_verified_history(self, limit=1000):
        """Retrieve archive for verified alerts with valid trajectory data."""
        try:
            import asyncio
            query = {"verified": True, "trajectories.0": {"$exists": True}}
            tasks = [self.db[coll].find(query).limit(limit).to_list(length=limit) for coll in [COLLECTION_SALVO, COLLECTION_DRONE]]
            results = await asyncio.gather(*tasks)
            unified = []
            for res in results:
                for item in res:
                    item.pop("_id", None)
                    unified.append(item)
            return unified
        except Exception as e:
            logger.error(f"VERIFIED_FETCH_FAILURE: {e}")
            return []

    async def merge_alerts(self, alert_type, alert_ids, engine=None):
        """
        Consolidate multiple historical alerts into a single record.
        1. Fetch all original documents.
        2. Use the cluster merging logic to generate a unified Master.
        3. Save the Master and delete the originals.
        """
        from src.utils.cluster_utils import merge_event_group
        
        collection = self.collections.get(alert_type)
        if collection is None: return None
        
        try:
            # 1. Fetch original documents
            cursor = collection.find({"id": {"$in": alert_ids}})
            docs = await cursor.to_list(length=len(alert_ids))
            if not docs: return None
            
            # 2. Convert to active_events format for merge_event_group
            # merge_event_group expects { id: { "data": payload } }
            pseudo_active_events = {
                doc["id"]: {"data": doc, "category": alert_type} for doc in docs
            }
            
            # 3. Generate Master Payload
            master_payload = await merge_event_group(alert_ids, pseudo_active_events, engine)
            if not master_payload: return None
            
            # 4. Save Master and Delete Originals
            # We use save_alert which handles upsert correctly
            await self.save_alert(alert_type, master_payload)
            
            # Delete other IDs (all except the new Master ID)
            # Standard merge_event_group uses the first ID in sorted list as Master
            master_id = master_payload["id"]
            to_delete = [aid for aid in alert_ids if aid != master_id]
            
            if to_delete:
                await collection.delete_many({"id": {"$in": to_delete}})
                logger.info(f"DB_MERGE_CLEANUP: {len(to_delete)} original records purged.")
            
            master_payload.pop("_id", None)
            return master_payload
        except Exception as e:
            logger.error(f"DB_MERGE_FAILURE: {alert_ids} - {e}")
            return None
