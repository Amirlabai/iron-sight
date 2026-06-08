import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.db.mongo_manager import MongoManager


@pytest.fixture
def mongo():
    mgr = MongoManager()
    mgr.event_logs = MagicMock()
    mgr.event_logs.find_one = AsyncMock()
    mgr.event_logs.update_one = AsyncMock()
    return mgr


class TestLogEventDedup:
    @pytest.mark.asyncio
    async def test_debounces_unchanged_updated_within_30s(self, mongo):
        now = datetime.now(timezone.utc)
        mongo.event_logs.find_one.return_value = {
            "city_count": 3,
            "timeline": [{"status": "UPDATED", "time": now.isoformat()}],
        }
        data = {"all_cities": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}

        await mongo.log_event("e1", "missiles", "UPDATED", data)

        mongo.event_logs.update_one.assert_awaited_once()
        update_op = mongo.event_logs.update_one.await_args[0][1]
        assert "$push" not in update_op
        assert "$inc" not in update_op
        assert "last_update_time" in update_op["$set"]

    @pytest.mark.asyncio
    async def test_writes_timeline_when_city_count_changes(self, mongo):
        mongo.event_logs.find_one.return_value = {
            "city_count": 2,
            "timeline": [{"status": "UPDATED", "time": datetime.now(timezone.utc).isoformat()}],
        }
        data = {"all_cities": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}

        await mongo.log_event("e1", "missiles", "UPDATED", data)

        update_op = mongo.event_logs.update_one.await_args[0][1]
        assert "$push" in update_op
        assert update_op["$inc"]["updates_count"] == 1

    @pytest.mark.asyncio
    async def test_writes_timeline_when_debounce_window_expired(self, mongo):
        old = datetime.now(timezone.utc) - timedelta(seconds=60)
        mongo.event_logs.find_one.return_value = {
            "city_count": 3,
            "timeline": [{"status": "UPDATED", "time": old.isoformat()}],
        }
        data = {"all_cities": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}

        await mongo.log_event("e1", "missiles", "UPDATED", data)

        update_op = mongo.event_logs.update_one.await_args[0][1]
        assert "$push" in update_op
