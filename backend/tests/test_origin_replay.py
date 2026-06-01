import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.engine import TrackingEngine
from src.core.origin_replay import build_origin_replay


@pytest.fixture
def engine():
    dm = MagicMock()
    dm.city_to_id = {}
    eng = TrackingEngine(dm, db_manager=None)
    eng.verified_history = []
    eng.last_sync_time = 0
    eng._sync_verified_history = AsyncMock()
    return eng


GAZA_CITIES = [
    {"name": "Ashkelon", "coords": [31.6693, 34.5715]},
    {"name": "Sderot", "coords": [31.5250, 34.5960]},
    {"name": "Ashdod", "coords": [31.8044, 34.6553]},
]

NORTH_CITIES = [
    {"name": "Tiberias", "coords": [32.7951, 35.5309]},
    {"name": "Safed", "coords": [32.9646, 35.4960]},
]

SOUTH_CITIES = [
    {"name": "BeerSheva", "coords": [31.2518, 34.7915]},
    {"name": "Ofakim", "coords": [31.3149, 34.6203]},
]


class TestBuildOriginReplay:
    @pytest.mark.asyncio
    async def test_gaza_salvo_includes_regional_projection(self, engine):
        result = await build_origin_replay(engine, GAZA_CITIES, allow_strategic=False)
        step_ids = [s["id"] for s in result["steps"]]

        assert "map_cities" in step_ids
        assert "regional_proj_0" in step_ids
        assert result["final"]["origin"] in ("Gaza", "Lebanon")

        regional = next(s for s in result["steps"] if s["id"] == "regional_proj_0")
        assert regional["decision"].get("depth") == 0.5

    @pytest.mark.asyncio
    async def test_multi_cluster_produces_multiple_origin_decisions(self, engine):
        cities = NORTH_CITIES + SOUTH_CITIES
        result = await build_origin_replay(engine, cities, allow_strategic=True)
        step_ids = [s["id"] for s in result["steps"]]

        decided = [s for s in step_ids if s.startswith("origin_decided_")]
        assert len(decided) >= 2
        assert "cluster" in step_ids

    @pytest.mark.asyncio
    async def test_strategic_gate_skips_strategic_projection(self, engine):
        result = await build_origin_replay(engine, GAZA_CITIES, allow_strategic=False)
        strategic_steps = [
            s for s in result["steps"]
            if s["id"].startswith("strategic_proj_")
        ]
        assert strategic_steps
        assert all(s["decision"].get("skipped") is True for s in strategic_steps)

    @pytest.mark.asyncio
    async def test_steps_end_with_final(self, engine):
        result = await build_origin_replay(engine, GAZA_CITIES)
        assert result["steps"][-1]["id"] == "final"
        assert result["final"]["trajectories"]


class TestGetProjectedOrigin:
    def test_ray_march_avoids_country_center_pin(self, engine):
        cities = [
            {"name": "Tiberias", "coords": [32.7951, 35.5309]},
            {"name": "Safed", "coords": [32.9646, 35.4960]},
        ]
        center = engine.origins["Lebanon"]
        proj = engine.get_projected_origin(cities, "Lebanon", depth=0.5)
        assert engine.get_distance(proj, center) > 0.05

    def test_projected_point_on_regression_ray(self, engine):
        cities = [
            {"name": "Ashkelon", "coords": [31.6693, 34.5715]},
            {"name": "Sderot", "coords": [31.5250, 34.5960]},
        ]
        centroid = engine._cluster_centroid(cities)
        oriented = engine._oriented_regression_vector(cities, centroid)
        assert oriented is not None
        v_lat, v_lon = oriented
        proj = engine.get_projected_origin(cities, "Gaza", depth=0.5)
        hit, depth = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Gaza", 0.5
        )
        if hit:
            assert engine.get_distance(proj, hit) < 0.001
        else:
            expected = engine._project_point(centroid, v_lat, v_lon, 0.5)
            assert engine.get_distance(proj, expected) < 0.001

    def test_regional_entry_inset_pushes_past_border(self, engine):
        cities = [
            {"name": "Tiberias", "coords": [32.7951, 35.5309]},
            {"name": "Safed", "coords": [32.9646, 35.4960]},
        ]
        centroid = engine._cluster_centroid(cities)
        v_lat, v_lon = engine._oriented_regression_vector(cities, centroid)
        orig_inset = engine.regional_entry_inset
        engine.regional_entry_inset = 0.0
        border_only, border_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Lebanon", 0.5, num_steps=50
        )
        engine.regional_entry_inset = orig_inset
        inset, inset_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Lebanon", 0.5, num_steps=50
        )
        assert border_only is not None and inset is not None
        assert inset_d > border_d
        assert engine.get_distance(inset, border_only) > 0.01
