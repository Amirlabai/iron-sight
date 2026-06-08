"""In-memory active event store: lightweight per-relay stubs + one canonical payload per cluster master."""

import hashlib
import json
import logging
from datetime import datetime

import numpy as np

from src.utils.cluster_utils import group_events

logger = logging.getLogger("IronSightTerminal")


class EventStore:
    """Stub+master store. Stubs hold per-relay city subsets; masters hold one shared analysis per cluster."""

    def __init__(self):
        self._stubs = {}
        self._masters = {}
        self._view_cache = None
        self._merge_cache_hash = None
        self._merge_cache_payloads = None

    def _invalidate(self):
        self._view_cache = None
        self._merge_cache_hash = None
        self._merge_cache_payloads = None

    def _invalidate_merge_only(self):
        self._merge_cache_hash = None
        self._merge_cache_payloads = None

    def __contains__(self, alert_id):
        return alert_id in self._stubs

    def __len__(self):
        return len(self._stubs)

    def __bool__(self):
        return bool(self._stubs)

    def items(self):
        return self.active_events.items()

    def keys(self):
        return self.active_events.keys()

    def values(self):
        return self.active_events.values()

    def get(self, alert_id, default=None):
        view = self.active_events
        if alert_id in view:
            return view[alert_id]
        return default

    def __getitem__(self, alert_id):
        return self.active_events[alert_id]

    def pop(self, alert_id, default=None):
        if alert_id not in self._stubs:
            return default
        stub = self._stubs.pop(alert_id)
        master_id = stub["master_id"]
        self._maybe_drop_master(master_id)
        self._invalidate()
        return stub

    @property
    def active_events(self):
        if self._view_cache is None:
            self._view_cache = self._build_view()
        return self._view_cache

    def has_active_newsflash(self):
        return any(
            s["category"] == "newsFlash" and s["end_time"] is None
            for s in self._stubs.values()
        )

    def _build_view(self):
        view = {}
        for aid, stub in self._stubs.items():
            view[aid] = self._stub_to_event(aid, stub)
        return view

    def _stub_to_event(self, aid, stub):
        master = self._masters[stub["master_id"]]
        member_cities = stub["member_cities"]
        data = dict(master["data"])
        data["all_cities"] = member_cities
        if member_cities:
            coords = np.array([c["coords"] for c in member_cities])
            data["center"] = np.mean(coords, axis=0).tolist()
        return {
            "data": data,
            "last_update_time": stub["last_update_time"],
            "end_time": stub["end_time"],
            "category": stub["category"],
            "is_transient": stub.get("is_transient", False),
            "lifecycle_status": stub.get("lifecycle_status"),
            "master_id": stub["master_id"],
        }

    def _clustering_view(self):
        """Union-city view for master assignment (matches broadcast merge geometry)."""
        view = {}
        union_cache = {}
        for aid, stub in self._stubs.items():
            master_id = stub["master_id"]
            if master_id not in union_cache:
                union_cache[master_id] = self._union_cities_for_master(master_id)
            union = union_cache[master_id]
            master = self._masters[master_id]
            data = dict(master["data"])
            data["all_cities"] = union
            if union:
                coords = np.array([c["coords"] for c in union])
                data["center"] = np.mean(coords, axis=0).tolist()
            view[aid] = {
                "data": data,
                "last_update_time": stub["last_update_time"],
                "end_time": stub["end_time"],
                "category": stub["category"],
                "is_transient": stub.get("is_transient", False),
                "lifecycle_status": stub.get("lifecycle_status"),
                "master_id": master_id,
            }
        return view

    def _maybe_drop_master(self, master_id):
        if any(s["master_id"] == master_id for s in self._stubs.values()):
            return
        self._masters.pop(master_id, None)

    def _union_cities_for_master(self, master_id):
        seen = {}
        for stub in self._stubs.values():
            if stub["master_id"] != master_id:
                continue
            for city in stub["member_cities"]:
                name = city.get("name")
                if name:
                    seen[name] = city
        return list(seen.values())

    def _resolve_master_id(self, alert_id):
        groups = group_events(self._clustering_view(), threshold_km=15, include_all=False)
        for group in groups:
            if alert_id in group:
                return sorted(group)[0]
        return alert_id

    def _cluster_stub_ids(self, master_id):
        return sorted(
            sid for sid, stub in self._stubs.items() if stub["master_id"] == master_id
        )

    async def _rebuild_master(
        self,
        master_id,
        processor,
        a_type,
        allow_strategic,
    ):
        union = self._union_cities_for_master(master_id)
        if not union:
            return None, 0
        full_analysis = await processor.process(
            a_type,
            [c["name"] for c in union],
            active_events=None,
            has_newsflash_in_batch=allow_strategic,
            use_polygon_hulls=False,
        )
        if not full_analysis:
            return None, len(union)
        lead_stub = self._stubs.get(master_id) or next(
            (self._stubs[sid] for sid in self._cluster_stub_ids(master_id) if sid in self._stubs),
            None,
        )
        if lead_stub:
            full_analysis["time"] = (
                self._masters[master_id]["data"].get("time")
                or lead_stub.get("event_time")
            )
        self._masters[master_id]["data"] = full_analysis
        self._masters[master_id]["dirty"] = True
        self._invalidate()
        return full_analysis, len(union)

    def compute_broadcast_hash(self):
        parts = []
        for aid in sorted(self._stubs.keys()):
            stub = self._stubs[aid]
            parts.append(
                (
                    aid,
                    stub["end_time"],
                    stub["last_update_time"],
                    len(stub["member_cities"]),
                    stub["master_id"],
                    self._masters[stub["master_id"]].get("dirty", False),
                )
            )
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def merge_cache_valid(self, state_hash):
        return self._merge_cache_hash == state_hash and self._merge_cache_payloads is not None

    def get_cached_merge_payloads(self):
        return self._merge_cache_payloads

    def set_merge_cache(self, state_hash, payloads):
        self._merge_cache_hash = state_hash
        self._merge_cache_payloads = payloads

    async def register_detection(
        self,
        alert_id,
        analysis,
        a_type,
        is_simulation,
        event_time,
        now,
        processor=None,
        has_newsflash_in_batch=False,
    ):
        member_cities = list(analysis.get("all_cities", []))
        analysis = dict(analysis)
        analysis["is_simulation"] = is_simulation
        analysis["time"] = event_time

        self._stubs[alert_id] = {
            "member_cities": member_cities,
            "last_update_time": now,
            "end_time": None,
            "category": a_type,
            "is_transient": a_type == "newsFlash",
            "lifecycle_status": None,
            "master_id": alert_id,
            "event_time": event_time,
        }
        self._masters[alert_id] = {"data": analysis, "dirty": True}
        self._invalidate()

        new_master_id = self._resolve_master_id(alert_id)
        if new_master_id != alert_id:
            self._stubs[alert_id]["master_id"] = new_master_id
            self._invalidate()
            if new_master_id not in self._masters:
                self._masters[new_master_id] = {"data": dict(analysis), "dirty": True}
            self._maybe_drop_master(alert_id)

        master_id = self._stubs[alert_id]["master_id"]
        allow_strategic = has_newsflash_in_batch or self.has_active_newsflash()
        if len(self._cluster_stub_ids(master_id)) > 1 and processor is not None:
            await self._rebuild_master(master_id, processor, a_type, allow_strategic)
            self._masters[master_id]["data"]["is_simulation"] = is_simulation
            self._masters[master_id]["data"]["time"] = event_time

        return len(member_cities)

    async def apply_rolling_update(
        self,
        alert_id,
        analysis,
        a_type,
        is_simulation,
        event_time,
        now,
        processor,
        allow_strategic,
    ):
        """Apply relay update. Returns (changed, new_city_count, total_cities) or (False, 0, 0) on duplicate."""
        stub = self._stubs[alert_id]
        existing_names = {c["name"] for c in stub["member_cities"] if c.get("name")}
        incoming_names = [c["name"] for c in analysis.get("all_cities", []) if c.get("name")]
        incoming_arr = np.array(incoming_names)
        existing_arr = np.array(list(existing_names)) if existing_names else np.array([])
        if existing_arr.size:
            is_new = ~np.isin(incoming_arr, existing_arr)
        else:
            is_new = np.ones(len(incoming_arr), dtype=bool)

        new_city_objs = [
            c for c, flag in zip(analysis["all_cities"], is_new) if flag and c.get("name")
        ]
        if not new_city_objs:
            logger.debug(f"ROLLING_UPDATE_SKIPPED: {alert_id} duplicate relay")
            return False, 0, len(stub["member_cities"])

        name_to_city = {c["name"]: c for c in stub["member_cities"] if c.get("name")}
        for c in new_city_objs:
            name_to_city[c["name"]] = c
        prev_cities = stub["member_cities"]
        prev_end_time = stub["end_time"]
        prev_last_update = stub["last_update_time"]
        stub["member_cities"] = list(name_to_city.values())
        stub["end_time"] = None
        stub["last_update_time"] = now
        self._invalidate()

        master_id = stub["master_id"]
        full_analysis, total = await self._rebuild_master(
            master_id, processor, a_type, allow_strategic
        )
        if not full_analysis:
            stub["member_cities"] = prev_cities
            stub["end_time"] = prev_end_time
            stub["last_update_time"] = prev_last_update
            self._invalidate()
            return False, 0, len(prev_cities)

        full_analysis["is_simulation"] = is_simulation
        full_analysis["time"] = (
            self._masters[master_id]["data"].get("time")
            or event_time
            or datetime.now().isoformat()
        )
        self._masters[master_id]["data"]["time"] = full_analysis["time"]

        self._sync_cluster_timeouts(master_id, alert_id, now, len(new_city_objs))
        return True, len(new_city_objs), total

    def _sync_cluster_timeouts(self, master_id, alert_id, now, new_city_count):
        if new_city_count <= 0:
            return
        siblings = self._cluster_stub_ids(master_id)
        if len(siblings) <= 1:
            return
        for sibling_id in siblings:
            if sibling_id != alert_id and sibling_id in self._stubs:
                self._stubs[sibling_id]["last_update_time"] = now
        logger.info(
            f"CLUSTER_TIMEOUT_SYNC: {len(siblings)} events synchronized (trigger: {alert_id})"
        )
        self._invalidate()

    def set_field(self, alert_id, field, value):
        if alert_id not in self._stubs:
            return
        self._stubs[alert_id][field] = value
        self._invalidate()

    def set_fields(self, alert_id, **fields):
        if alert_id not in self._stubs:
            return
        self._stubs[alert_id].update(fields)
        self._invalidate()

    def master_data_for_persist(self, master_id):
        master = self._masters.get(master_id)
        return master["data"] if master else None

    def memory_stats(self):
        unique_cities = set()
        for stub in self._stubs.values():
            for c in stub["member_cities"]:
                if c.get("name"):
                    unique_cities.add(c["name"])
        return {
            "members": len(self._stubs),
            "masters": len(self._masters),
            "unique_cities": len(unique_cities),
        }

    def log_memory_stats(self):
        stats = self.memory_stats()
        logger.info(
            f"ACTIVE_MEMORY: {stats['members']} members, "
            f"{stats['masters']} masters, {stats['unique_cities']} unique cities"
        )
