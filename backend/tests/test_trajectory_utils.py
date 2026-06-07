from unittest.mock import MagicMock

import pytest

from src.core.origin_ml import collapse_missile_origins
from src.utils.trajectory_utils import (
    apply_projected_origin,
    entry_by_origin,
    set_trajectory_entry,
    sync_missile_trajectory_on_verify,
)


class TestSetTrajectoryEntry:
    def test_sets_both_coord_fields(self):
        traj = {"origin": "Lebanon"}
        set_trajectory_entry(traj, [33.2, 35.3])
        assert traj["origin_coords"] == [33.2, 35.3]
        assert traj["marker_coords"] == [33.2, 35.3]


class TestEntryByOrigin:
    def test_projects_each_candidate(self):
        engine = MagicMock()
        engine.strategic_depths = {"Lebanon": 0.5, "Gaza": 0.5}
        engine.project_calc_entry = MagicMock(side_effect=lambda cities, origin, depth: [33.0, 35.0])

        result = entry_by_origin(engine, [{"coords": [32.8, 35.5]}], ["Lebanon", "Gaza"])

        assert result["Lebanon"] == [33.0, 35.0]
        assert result["Gaza"] == [33.0, 35.0]
        assert engine.project_calc_entry.call_count == 2

    def test_skips_origins_without_calc_hit(self):
        engine = MagicMock()
        engine.strategic_depths = {"Lebanon": 0.5}
        engine.project_calc_entry = MagicMock(return_value=None)

        result = entry_by_origin(engine, [{"coords": [32.8, 35.5]}], ["Lebanon"])
        assert result == {}


class TestApplyProjectedOrigin:
    def test_clears_stale_calc_entry_coords(self):
        engine = MagicMock()
        engine.project_origin_display = MagicMock(return_value=([33.5, 35.5], None))
        traj = {"calc_entry_coords": [33.4, 35.4]}

        apply_projected_origin(engine, traj, [{"coords": [32.8, 35.5]}], "Lebanon", 0.5)

        assert "calc_entry_coords" not in traj
        assert traj["origin_coords"] == [33.5, 35.5]


class TestCollapseMissileOriginsCoords:
    def test_origin_and_marker_match_border_entry(self):
        engine = MagicMock()
        engine.strategic_depths = {"Lebanon": 0.5, "Iran": 16.0}
        engine.origins = {"Lebanon": [33.9, 35.7]}
        engine.zoom_levels = {"Lebanon": 8}
        engine.get_projected_origin = MagicMock(return_value=[33.5, 35.5])
        engine.project_origin_display = MagicMock(return_value=([33.5, 35.5], [33.4, 35.4]))

        payload = {
            "clusters": [{"origin": "Iran", "cities": []}],
            "trajectories": [{"origin": "Iran"}, {"origin": "Lebanon"}],
            "all_cities": [{"name": "X", "coords": [32.8, 35.5]}],
        }
        collapse_missile_origins(payload, "Lebanon", 0.9, {"Iran": 0.1, "Lebanon": 0.9}, "ml", engine)

        traj = payload["trajectories"][0]
        assert traj["origin_coords"] == [33.5, 35.5]
        assert traj["marker_coords"] == [33.5, 35.5]


class TestSyncMissileTrajectoryOnVerify:
    def test_rewrites_full_trajectory(self):
        engine = MagicMock()
        engine.strategic_depths = {"Lebanon": 0.5, "Gaza": 0.5}
        engine.zoom_levels = {"Lebanon": 7, "Gaza": 8}

        traj = {
            "origin": "Gaza",
            "origin_coords": [31.4, 34.3],
            "marker_coords": [31.4, 34.3],
            "target_coords": [32.0, 34.0],
            "depth": 0.5,
        }
        cities = [
            {"name": "A", "coords": [32.8, 35.5]},
            {"name": "B", "coords": [32.9, 35.6]},
        ]

        sync_missile_trajectory_on_verify(
            traj, "Lebanon", [33.2, 35.3], cities, engine
        )

        assert traj["origin"] == "Lebanon"
        assert traj["origin_coords"] == [33.2, 35.3]
        assert traj["marker_coords"] == [33.2, 35.3]
        assert traj["depth"] == 0.5
        assert traj["zoom"] == 7
        assert traj["target_coords"][0] == pytest.approx(32.85)
        assert traj["target_coords"][1] == pytest.approx(35.55)
