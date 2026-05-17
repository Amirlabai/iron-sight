from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.push_manager import PushManager, _prune_last_notified


class TestPruneLastNotified:
    def test_should_return_empty_dict_when_input_is_none(self):
        assert _prune_last_notified(None, {"a"}) == {}

    def test_should_drop_keys_not_in_active_alert_ids(self):
        last = {"a": "k1", "b": "k2", "c": "k3"}
        assert _prune_last_notified(last, {"a", "c"}) == {"a": "k1", "c": "k3"}

    def test_should_keep_only_last_fifty_entries_when_over_limit(self):
        last = {f"id{i}": f"k{i}" for i in range(60)}
        active = set(last.keys())
        pruned = _prune_last_notified(last, active)
        assert len(pruned) == 50
        assert "id59" in pruned
        assert "id0" not in pruned


class TestPushManagerUpsert:
    @pytest.fixture
    def manager(self):
        db = MagicMock()
        db.db = MagicMock()
        db.get_push_subscription = AsyncMock(return_value=None)
        db.upsert_push_subscription = AsyncMock()
        mgr = PushManager(db)
        mgr._vapid_ready = True
        return mgr

    @pytest.mark.asyncio
    async def test_should_reject_when_not_configured(self):
        mgr = PushManager(MagicMock())
        mgr._vapid_ready = False
        ok, err, token = await mgr.upsert_subscription({})
        assert ok is False
        assert err == "Push service unavailable"
        assert token is None

    @pytest.mark.asyncio
    async def test_should_reject_invalid_subscription(self, manager):
        ok, err, token = await manager.upsert_subscription({"subscription": {}})
        assert ok is False
        assert err == "Invalid subscription"
        assert token is None

    @pytest.mark.asyncio
    async def test_should_reject_invalid_scope(self, manager):
        body = {
            "subscription": {
                "endpoint": "https://push.example/x",
                "keys": {"p256dh": "a", "auth": "b"},
            },
            "scope": "invalid",
        }
        ok, err, token = await manager.upsert_subscription(body)
        assert ok is False
        assert err == "Invalid scope"

    @pytest.mark.asyncio
    async def test_should_upsert_valid_subscription(self, manager):
        body = {
            "subscription": {
                "endpoint": "https://push.example/x",
                "keys": {"p256dh": "a", "auth": "b"},
            },
            "scope": "radius",
            "radius_km": 12,
            "location": {"lat": 32.0, "lng": 34.0},
        }
        ok, err, token = await manager.upsert_subscription(body)
        assert ok is True
        assert err is None
        assert isinstance(token, str)
        manager.db.upsert_push_subscription.assert_awaited_once()
