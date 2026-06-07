"""Script entry points delegate to archive_normalize (not coord-only Gaza/Lebanon patch)."""

import importlib.util
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.engine import TrackingEngine
from src.utils.archive_normalize import (
    dedupe_verified_missile_archive,
    normalize_missile_archive,
)

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "recalc_regional_trajectories.py"
spec = importlib.util.spec_from_file_location("recalc_regional", SCRIPT_PATH)
recalc_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recalc_mod)

LEBANON_CITIES = [
    {"name": "Tiberias", "coords": [32.7951, 35.5309]},
    {"name": "Safed", "coords": [32.9646, 35.4960]},
]


@pytest.fixture
def engine():
    dm = MagicMock()
    dm.city_to_id = {}
    eng = TrackingEngine(dm, db_manager=None)
    eng.verified_history = []
    eng._sync_verified_history = AsyncMock()
    return eng


class TestRecalcScriptUsesArchiveNormalize:
    def test_script_wires_normalize_helpers(self):
        assert recalc_mod.normalize_missile_archive is normalize_missile_archive
        assert recalc_mod.dedupe_verified_missile_archive is dedupe_verified_missile_archive

    @pytest.mark.asyncio
    async def test_run_refuses_write_without_all(self, engine):
        with patch.dict(os.environ, {"MONGO_URI": "mongodb://test"}, clear=False):
            with pytest.raises(SystemExit):
                await recalc_mod.run(limit=1, dry_run=False, dedupe_verified=False)

    @pytest.mark.asyncio
    async def test_run_invokes_normalize_for_unverified(self, engine):
        doc = {
            "id": "test-alert",
            "all_cities": LEBANON_CITIES,
            "trajectories": [{"origin": "Lebanon"}],
        }

        class AsyncCursor:
            def __init__(self, rows):
                self._rows = rows

            def sort(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def __aiter__(self):
                self._iter = iter(self._rows)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        mock_collection = MagicMock()
        mock_collection.find.return_value = AsyncCursor([{**doc, "_id": 1}])
        mock_db = MagicMock()
        mock_db.collections = {"missiles": mock_collection}

        with patch.dict(os.environ, {"MONGO_URI": "mongodb://test"}, clear=False):
            with patch.object(recalc_mod, "MongoManager", return_value=mock_db):
                with patch.object(recalc_mod, "LamasDataManager") as mock_dm_cls:
                    mock_dm_cls.return_value.load = AsyncMock()
                    with patch.object(recalc_mod, "TrackingEngine", return_value=engine):
                        with patch.object(
                            recalc_mod,
                            "normalize_missile_archive",
                            new_callable=AsyncMock,
                        ) as mock_norm:
                            mock_norm.return_value = (doc, True, ["rebuild_clusters"])
                            await recalc_mod.run(limit=1, dry_run=True, dedupe_verified=False)
                            mock_norm.assert_called_once()

    def test_dedupe_verified_uses_helper(self, engine):
        stored = [33.20, 35.28]
        alert = {
            "verified": True,
            "manual_origin": "Lebanon",
            "all_cities": LEBANON_CITIES,
            "trajectories": [
                {"origin": "Lebanon", "origin_coords": stored, "marker_coords": stored},
                {"origin": "Iran", "origin_coords": [32.0, 53.0], "marker_coords": [32.0, 53.0]},
            ],
            "clusters": [],
        }
        _, changed, labels = dedupe_verified_missile_archive(alert, engine=engine)
        assert changed is True
        assert len(alert["trajectories"]) == 1
        assert alert["trajectories"][0]["origin_coords"] == stored

    @pytest.mark.asyncio
    async def test_normalize_skips_committed_without_dedupe_flag(self, engine):
        alert = {
            "verified": True,
            "manual_origin": "Lebanon",
            "all_cities": LEBANON_CITIES,
            "trajectories": [{"origin": "Lebanon", "origin_coords": [33.2, 35.28]}],
        }
        _, changed, _ = await normalize_missile_archive(engine, alert)
        assert changed is False
