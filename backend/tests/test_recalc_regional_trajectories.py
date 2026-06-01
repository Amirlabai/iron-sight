import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.origin_replay import build_origin_replay

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
    from unittest.mock import AsyncMock
    dm = MagicMock()
    dm.city_to_id = {}
    from src.core.engine import TrackingEngine
    eng = TrackingEngine(dm, db_manager=None)
    eng.verified_history = []
    eng._sync_verified_history = AsyncMock()
    return eng


class TestRecalcRegionalTrajectories:
    def test_verified_syncs_origin_to_marker(self, engine):
        alert = {
            "verified": True,
            "manual_origin": "Lebanon",
            "all_cities": LEBANON_CITIES,
            "trajectories": [{
                "origin": "Lebanon",
                "origin_coords": [33.09, 35.64],
                "marker_coords": [33.20, 35.28],
                "target_coords": [32.79, 35.51],
                "depth": 0.5,
            }],
        }
        changed, detail = recalc_mod._recalc_document(engine, alert)
        assert changed is True
        assert detail[0]["mode"] == "verified_sync"
        assert alert["trajectories"][0]["origin_coords"] == [33.20, 35.28]
        assert alert["trajectories"][0]["marker_coords"] == [33.20, 35.28]

    def test_unverified_syncs_both_coords(self, engine):
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
        changed, _detail = recalc_mod._recalc_document(engine, alert)
        assert changed is True
        traj = alert["trajectories"][0]
        assert traj["origin_coords"] == traj["marker_coords"]
        center = engine.origins["Lebanon"]
        assert traj["origin_coords"] != center or engine.get_distance(traj["origin_coords"], center) < 0.01

    def test_unverified_uses_ray_march(self, engine):
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
        changed, _detail = recalc_mod._recalc_document(engine, alert)
        assert changed is True
        entry = alert["trajectories"][0]["origin_coords"]
        center = engine.origins["Lebanon"]
        assert entry != center or engine.get_distance(entry, center) < 0.01


class TestVerifiedOriginReplay:
    @pytest.mark.asyncio
    async def test_verified_stored_coords_on_trajectories_step(self, engine):
        stored = {
            "verified": True,
            "manual_origin": "Lebanon",
            "trajectories": [{
                "origin": "Lebanon",
                "origin_coords": [33.20, 35.28],
                "marker_coords": [33.20, 35.28],
                "target_coords": [33.0821, 35.1443],
                "depth": 0.5,
            }],
        }
        result = await build_origin_replay(
            engine, LEBANON_CITIES, stored=stored, allow_strategic=False
        )
        traj_step = next(s for s in result["steps"] if s["id"] == "trajectories")
        assert traj_step["decision"].get("method") == "verified_manual"
        entry = result["final"]["trajectories"][0]["origin_coords"]
        assert entry == [33.20, 35.28]
        line = traj_step["visuals"]["polylines"][0]["points"]
        assert line[0] == [33.20, 35.28]
