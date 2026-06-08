import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.event_store import EventStore


def _city(name, lat=32.0, lon=34.0):
    return {"name": name, "coords": [lat, lon], "area": "מרכז"}


def _analysis(cities, category="missiles"):
    return {
        "category": category,
        "all_cities": cities,
        "clusters": [{"cities": cities, "hull": [[32, 34]]}],
        "trajectories": [],
        "center": [32.0, 34.0],
    }


@pytest.fixture
def processor():
    proc = MagicMock()
    proc.process = AsyncMock(side_effect=lambda a_type, names, *a, **kw: _analysis(
        [_city(n) for n in names], category=a_type
    ))
    return proc


class TestEventStoreNoOpSkip:
    @pytest.mark.asyncio
    async def test_duplicate_relay_skips_reprocess(self, processor):
        store = EventStore()
        cities = [_city("A"), _city("B")]
        await store.register_detection(
            "id1", _analysis(cities), "missiles", False, "2026-01-01T00:00:00", 1.0,
            processor=processor, has_newsflash_in_batch=False,
        )
        processor.process.reset_mock()

        changed, new_count, total = await store.apply_rolling_update(
            "id1",
            _analysis(cities),
            "missiles",
            False,
            "2026-01-01T00:00:00",
            2.0,
            processor,
            False,
        )
        assert changed is False
        assert new_count == 0
        assert processor.process.await_count == 0

    @pytest.mark.asyncio
    async def test_new_cities_trigger_single_reprocess(self, processor):
        store = EventStore()
        await store.register_detection(
            "id1",
            _analysis([_city("A")]),
            "missiles",
            False,
            "2026-01-01T00:00:00",
            1.0,
            processor=processor,
        )
        processor.process.reset_mock()

        changed, new_count, total = await store.apply_rolling_update(
            "id1",
            _analysis([_city("A"), _city("B")]),
            "missiles",
            False,
            "2026-01-01T00:00:00",
            2.0,
            processor,
            False,
        )
        assert changed is True
        assert new_count == 1
        assert processor.process.await_count == 1


class TestEventStoreClusterMaster:
    @pytest.mark.asyncio
    async def test_members_share_master_data(self, processor):
        store = EventStore()
        await store.register_detection(
            "aaa",
            _analysis([_city("A")], category="missiles"),
            "missiles",
            False,
            "t1",
            1.0,
            processor=processor,
        )
        await store.register_detection(
            "bbb",
            _analysis([_city("A"), _city("B")], category="missiles"),
            "missiles",
            False,
            "t2",
            2.0,
            processor=processor,
        )
        view = store.active_events
        master_a = view["aaa"]["master_id"]
        master_b = view["bbb"]["master_id"]
        assert master_a == master_b
        assert store._masters[master_a]["data"] is store._masters[master_b]["data"]


class TestEventStoreMergeCache:
    def test_cache_invalidates_on_stub_mutation(self):
        store = EventStore()
        store._stubs["a"] = {
            "member_cities": [_city("X")],
            "last_update_time": 1.0,
            "end_time": None,
            "category": "missiles",
            "is_transient": False,
            "lifecycle_status": None,
            "master_id": "a",
            "event_time": "t",
        }
        store._masters["a"] = {"data": _analysis([_city("X")]), "dirty": False}
        h = store.compute_broadcast_hash()
        store.set_merge_cache(h, [{"id": "x"}])
        assert store.merge_cache_valid(h) is True
        store.set_field("a", "last_update_time", 2.0)
        assert store.merge_cache_valid(h) is False

    def test_broadcast_hash_changes_on_end_time(self):
        store = EventStore()
        store._stubs["a"] = {
            "member_cities": [_city("X")],
            "last_update_time": 1.0,
            "end_time": None,
            "category": "missiles",
            "is_transient": False,
            "lifecycle_status": None,
            "master_id": "a",
            "event_time": "t",
        }
        store._masters["a"] = {"data": _analysis([_city("X")]), "dirty": False}
        h1 = store.compute_broadcast_hash()
        store._stubs["a"]["end_time"] = 99.0
        h2 = store.compute_broadcast_hash()
        assert h1 != h2
