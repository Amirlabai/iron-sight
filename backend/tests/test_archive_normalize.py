"""Tests for legacy missile archive normalization."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.engine import TrackingEngine
from src.utils.archive_normalize import (
    dedupe_verified_missile_archive,
    is_history_fixer_committed,
    normalize_missile_archive,
)

LEBANON_CITIES = [
    {"name": "Tiberias", "coords": [32.7951, 35.5309]},
    {"name": "Safed", "coords": [32.9646, 35.4960]},
    {"name": "Kiryat Shmona", "coords": [33.2079, 35.5702]},
]


@pytest.fixture
def engine():
    dm = MagicMock()
    dm.city_to_id = {}
    eng = TrackingEngine(dm, db_manager=None)
    eng.verified_history = []
    eng.last_sync_time = 0
    eng._sync_verified_history = AsyncMock()
    return eng


class TestHistoryFixerCommitted:
    def test_verified_or_manual_origin(self):
        assert is_history_fixer_committed({"verified": True})
        assert is_history_fixer_committed({"manual_origin": "Lebanon"})
        assert not is_history_fixer_committed({"trajectories": [{}]})


class TestNormalizeMissileArchive:
    @pytest.mark.asyncio
    async def test_skips_verified_rows(self, engine):
        stored_coords = [33.20, 35.28]
        alert = {
            "verified": True,
            "manual_origin": "Lebanon",
            "all_cities": LEBANON_CITIES,
            "trajectories": [{
                "origin": "Lebanon",
                "origin_coords": stored_coords,
                "marker_coords": stored_coords,
                "target_coords": [32.79, 35.51],
                "depth": 0.5,
            }],
            "clusters": [{"origin": "Lebanon", "cities": LEBANON_CITIES, "hull": []}],
        }
        _, changed, labels = await normalize_missile_archive(engine, alert)
        assert changed is False
        assert labels == []
        assert alert["trajectories"][0]["origin_coords"] == stored_coords

    @pytest.mark.asyncio
    async def test_collapses_legacy_multi_trajectory(self, engine):
        alert = {
            "all_cities": LEBANON_CITIES,
            "title": "Mixed Salvo",
            "trajectories": [
                {
                    "origin": "Lebanon",
                    "origin_coords": [33.88, 35.86],
                    "marker_coords": [33.88, 35.86],
                    "target_coords": [32.79, 35.51],
                    "depth": 0.5,
                },
                {
                    "origin": "Iran",
                    "origin_coords": [32.0, 53.0],
                    "marker_coords": [32.0, 53.0],
                    "target_coords": [32.79, 35.51],
                    "depth": 16.0,
                },
            ],
            "clusters": [
                {"origin": "Lebanon", "cities": [LEBANON_CITIES[0]], "hull": [[32.79, 35.53]]},
                {"origin": "Iran", "cities": [LEBANON_CITIES[1]], "hull": [[32.96, 35.50]]},
            ],
        }
        _, changed, labels = await normalize_missile_archive(engine, alert)
        assert changed is True
        assert len(alert["trajectories"]) == 1
        assert alert["trajectories"][0]["origin"] == "Lebanon"
        assert len(alert["clusters"]) == 1
        assert alert["clusters"][0]["origin"] == "Lebanon"
        assert len(alert["clusters"][0]["cities"]) == len(LEBANON_CITIES)
        assert "collapse_trajectories" in labels or "rebuild_clusters" in labels

    @pytest.mark.asyncio
    async def test_refreshes_display_geometry(self, engine):
        alert = {
            "all_cities": LEBANON_CITIES,
            "trajectories": [{
                "origin": "Lebanon",
                "origin_coords": [33.88, 35.86],
                "marker_coords": [33.88, 35.86],
                "target_coords": [32.79, 35.51],
                "depth": 0.5,
            }],
        }
        _, changed, _labels = await normalize_missile_archive(engine, alert)
        assert changed is True
        traj = alert["trajectories"][0]
        assert traj["origin_coords"] == traj["marker_coords"]
        center = engine.origins["Lebanon"]
        assert traj["origin_coords"] != center or engine.get_distance(traj["origin_coords"], center) < 0.01


class TestDedupeVerifiedMissileArchive:
    def test_drops_extra_trajectories_without_moving_coords(self, engine):
        stored = [33.20, 35.28]
        alert = {
            "verified": True,
            "manual_origin": "Lebanon",
            "all_cities": LEBANON_CITIES,
            "title": "Old Title",
            "trajectories": [
                {
                    "origin": "Lebanon",
                    "origin_coords": stored,
                    "marker_coords": stored,
                    "target_coords": [32.79, 35.51],
                    "depth": 0.5,
                },
                {
                    "origin": "Iran",
                    "origin_coords": [32.0, 53.0],
                    "marker_coords": [32.0, 53.0],
                    "target_coords": [32.79, 35.51],
                    "depth": 16.0,
                },
            ],
            "clusters": [
                {"origin": "Iran", "cities": [LEBANON_CITIES[0]], "hull": [[32.79, 35.53]]},
                {"origin": "Lebanon", "cities": [LEBANON_CITIES[1]], "hull": [[32.96, 35.50]]},
            ],
        }
        _, changed, labels = dedupe_verified_missile_archive(alert, engine=engine)
        assert changed is True
        assert len(alert["trajectories"]) == 1
        assert alert["trajectories"][0]["origin_coords"] == stored
        assert alert["title"] == "Lebanon Salvo"
        assert len(alert["clusters"]) == 1
        assert alert["clusters"][0]["origin"] == "Lebanon"
        assert "dedupe_trajectories" in labels
        assert "merge_clusters" in labels

    def test_skips_unverified(self, engine):
        alert = {
            "all_cities": LEBANON_CITIES,
            "trajectories": [{"origin": "Lebanon"}, {"origin": "Iran"}],
        }
        _, changed, labels = dedupe_verified_missile_archive(alert, engine=engine)
        assert changed is False
        assert len(alert["trajectories"]) == 2
