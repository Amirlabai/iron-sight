from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.mongo_manager import MongoManager


class TestVerifyPushClient:
    @pytest.fixture
    def manager(self):
        mgr = MongoManager.__new__(MongoManager)
        mgr.push_subscriptions = MagicMock()
        mgr.push_subscriptions.find_one = AsyncMock()
        return mgr

    @pytest.mark.asyncio
    async def test_should_return_false_when_endpoint_missing(self, manager):
        assert await manager.verify_push_client(None, "token") is False

    @pytest.mark.asyncio
    async def test_should_return_false_when_client_token_missing(self, manager):
        assert await manager.verify_push_client("https://ep", None) is False

    @pytest.mark.asyncio
    async def test_should_return_true_when_document_exists(self, manager):
        manager.push_subscriptions.find_one.return_value = {"_id": "x"}
        assert await manager.verify_push_client("https://ep", "tok") is True
        manager.push_subscriptions.find_one.assert_awaited_once_with(
            {"endpoint": "https://ep", "client_token": "tok"},
            projection={"_id": 1},
        )

    @pytest.mark.asyncio
    async def test_should_return_false_when_document_missing(self, manager):
        manager.push_subscriptions.find_one.return_value = None
        assert await manager.verify_push_client("https://ep", "bad") is False
