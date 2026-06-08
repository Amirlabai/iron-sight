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


class DummyCursor:
    def __init__(self, rows):
        self.rows = rows
        self.skipped = 0
        self.limited = None

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, value):
        self.skipped = value
        return self

    def limit(self, value):
        self.limited = value
        return self

    async def to_list(self, length=None):
        start = self.skipped
        end = start + (self.limited if self.limited is not None else len(self.rows))
        sliced = self.rows[start:end]
        return [dict(item) for item in sliced[:length] if length is not None] if length is not None else sliced


class DummyCollection:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def find(self, query):
        self.last_query = query
        return DummyCursor(self.rows)


class TestHistoryPagination:
    @pytest.fixture
    def manager(self):
        mgr = MongoManager.__new__(MongoManager)
        mgr.collections = {
            "missiles": DummyCollection([
                {"_id": "1", "id": "5"},
                {"_id": "2", "id": "4"},
                {"_id": "3", "id": "3"},
                {"_id": "4", "id": "2"},
            ]),
            "hostileAircraftIntrusion": DummyCollection([
                {"_id": "5", "id": "8"},
                {"_id": "6", "id": "7"},
            ]),
        }
        return mgr

    @pytest.mark.asyncio
    async def test_should_apply_offset_and_limit_to_get_history(self, manager):
        result = await manager.get_history("missiles", limit=2, offset=1)
        assert [r["id"] for r in result] == ["4", "3"]
        assert all("_id" not in r for r in result)

    @pytest.mark.asyncio
    async def test_should_page_after_consolidation_sort(self, manager):
        result = await manager.get_consolidated_history(limit=2, offset=1)
        # Consolidated sorted desc IDs = 8,7,5,4,3,2 -> page from offset 1 = 7,5
        assert [r["id"] for r in result] == ["7", "5"]

    @pytest.mark.asyncio
    async def test_should_report_has_more_on_consolidated_page(self, manager):
        items, has_more = await manager.get_consolidated_history_page(limit=2, offset=0)
        assert [r["id"] for r in items] == ["8", "7"]
        assert has_more is True

    @pytest.mark.asyncio
    async def test_should_exclude_newsflash_from_consolidated(self, manager):
        manager.collections["newsFlash"] = DummyCollection([
            {"_id": "99", "id": "99", "category": "newsFlash"},
        ])
        result = await manager.get_consolidated_history(limit=10, offset=0)
        assert all(r["id"] != "99" for r in result)
