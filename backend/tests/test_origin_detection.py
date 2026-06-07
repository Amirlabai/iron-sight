"""Detect each calc-border origin: Gaza, Lebanon, Iran, North Iran, Yemen."""

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.engine import TrackingEngine

GAZA_CITIES = [
    {"name": "Ofakim", "coords": [31.3149, 34.6203]},
    {"name": "BeerSheva", "coords": [31.2518, 34.7915]},
    {"name": "Rahat", "coords": [31.3927, 34.7540]},
]

LEBANON_CITIES = [
    {"name": "Tiberias", "coords": [32.7951, 35.5309]},
    {"name": "Safed", "coords": [32.9646, 35.4960]},
    {"name": "Kiryat Shmona", "coords": [33.2079, 35.5702]},
]

NORTH_IRAN_CITIES = [
    {"name": "Haifa", "coords": [32.7940, 34.9896]},
    {"name": "Nahariya", "coords": [33.0059, 35.0989]},
    {"name": "Karmiel", "coords": [32.9194, 35.3030]},
]

YEMEN_CITIES = [
    {"name": "BeerSheva", "coords": [31.2518, 34.7915]},
    {"name": "Mitzpe Ramon", "coords": [30.6103, 34.8014]},
    {"name": "Eilat", "coords": [29.5577, 34.9519]},
]

# Southern Iran calc polygon — no natural 3-city cluster hits it; use aligned ray.
IRAN_SOUTHERN_CENTROID = [31.5, 34.5]
IRAN_SOUTHERN_TARGET = [27.37, 44.52]


@pytest.fixture
def engine():
    dm = MagicMock()
    dm.city_to_id = {}
    return TrackingEngine(dm, db_manager=None)


@pytest.fixture
def trace_engine():
    dm = MagicMock()
    dm.city_to_id = {}
    eng = TrackingEngine(dm, db_manager=None)
    eng.verified_history = []
    eng.last_sync_time = 0
    eng._sync_verified_history = AsyncMock()
    return eng


def _oriented_vector(engine, cities):
    centroid = engine._cluster_centroid(cities)
    oriented = engine._oriented_regression_vector(cities, centroid)
    assert oriented is not None, "Fixture must yield a regression vector"
    return centroid, oriented[0], oriented[1]


def _unit_vector_to(target, source):
    delta = np.array(target, dtype=float) - np.array(source, dtype=float)
    mag = np.linalg.norm(delta)
    assert mag > 0
    return delta[0] / mag, delta[1] / mag


def _assert_hit_in_polygon(engine, hit, poly_name, *, use_tactical=True):
    assert hit is not None
    assert engine.is_point_in_polygon(hit, poly_name, use_tactical=use_tactical)


class TestCalcBorderOriginDetection:
    """Ray march must enter the correct calculation border for each origin."""

    def test_detects_gaza(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, GAZA_CITIES)
        hit, depth = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Gaza", engine._projection_max_depth("Gaza", None)
        )
        _assert_hit_in_polygon(engine, hit, "Gaza", use_tactical=False)
        assert depth is not None and depth > 0
        assert not engine.is_point_in_polygon(hit, "Lebanon", use_tactical=False)

    def test_detects_lebanon(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, LEBANON_CITIES)
        hit, depth = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Lebanon", engine._projection_max_depth("Lebanon", None)
        )
        _assert_hit_in_polygon(engine, hit, "Lebanon", use_tactical=False)
        assert depth is not None and depth > 0
        assert not engine.is_point_in_polygon(hit, "Gaza", use_tactical=False)

    def test_detects_north_iran(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, NORTH_IRAN_CITIES)
        hit, depth = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "North Iran", engine._projection_max_depth("North Iran", None)
        )
        _assert_hit_in_polygon(engine, hit, "North Iran", use_tactical=False)
        assert depth is not None and depth > 0
        assert not engine.is_point_in_polygon(hit, "Iran", use_tactical=False)

    def test_detects_iran_southern(self, engine):
        v_lat, v_lon = _unit_vector_to(IRAN_SOUTHERN_TARGET, IRAN_SOUTHERN_CENTROID)
        hit, depth = engine._ray_march_calc_entry(
            IRAN_SOUTHERN_CENTROID, v_lat, v_lon, "Iran", 16.0
        )
        _assert_hit_in_polygon(engine, hit, "Iran", use_tactical=False)
        assert depth is not None and depth > 0
        assert not engine.is_point_in_polygon(hit, "North Iran", use_tactical=False)

    def test_detects_yemen(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, YEMEN_CITIES)
        hit, depth = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Yemen", engine._projection_max_depth("Yemen", None)
        )
        _assert_hit_in_polygon(engine, hit, "Yemen", use_tactical=False)
        assert depth is not None and depth > 0
        assert not engine.is_point_in_polygon(hit, "Gaza", use_tactical=False)


class TestTerritoryProjectionDetection:
    """Strategic/regional projection at standard depths hits each territory."""

    def test_gaza_at_regional_depth(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, GAZA_CITIES)
        hit, _ = engine._match_territory_at_projection(
            centroid, v_lat, v_lon, 0.5, ["Lebanon", "Gaza"]
        )
        assert hit == "Gaza"

    def test_lebanon_at_regional_depth(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, LEBANON_CITIES)
        hit, _ = engine._match_territory_at_projection(
            centroid, v_lat, v_lon, 0.5, ["Lebanon", "Gaza"]
        )
        assert hit == "Lebanon"

    def test_north_iran_at_strategic_depth(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, NORTH_IRAN_CITIES)
        hit, proj = engine._match_territory_at_projection(
            centroid, v_lat, v_lon, 7, ["North Iran", "Iran", "Yemen"]
        )
        assert hit == "North Iran"
        _assert_hit_in_polygon(engine, proj, "North Iran", use_tactical=False)

    def test_iran_southern_at_strategic_depth(self, engine):
        v_lat, v_lon = _unit_vector_to(IRAN_SOUTHERN_TARGET, IRAN_SOUTHERN_CENTROID)
        hit, proj = engine._match_territory_at_projection(
            IRAN_SOUTHERN_CENTROID, v_lat, v_lon, 7, ["North Iran", "Iran", "Yemen"]
        )
        assert hit == "Iran"
        _assert_hit_in_polygon(engine, proj, "Iran", use_tactical=False)
        assert not engine.is_point_in_polygon(proj, "North Iran", use_tactical=False)

    def test_yemen_at_strategic_depth(self, engine):
        centroid, v_lat, v_lon = _oriented_vector(engine, YEMEN_CITIES)
        hit, proj = engine._match_territory_at_projection(
            centroid, v_lat, v_lon, 7, ["North Iran", "Iran", "Yemen"]
        )
        assert hit == "Yemen"
        _assert_hit_in_polygon(engine, proj, "Yemen", use_tactical=False)


class TestTraceClusterOriginDetection:
    """End-to-end origin label from cluster city geometry."""

    @pytest.mark.asyncio
    async def test_detects_gaza(self, trace_engine):
        trace = await trace_engine.trace_cluster_origin(GAZA_CITIES, allow_strategic=True)
        assert trace["method"] == "regional_projection"
        assert trace["origin"] == "Gaza"
        assert trace["regional_hit"] == "Gaza"

    @pytest.mark.asyncio
    async def test_detects_lebanon(self, trace_engine):
        trace = await trace_engine.trace_cluster_origin(LEBANON_CITIES, allow_strategic=True)
        assert trace["method"] == "regional_projection"
        assert trace["origin"] == "Lebanon"
        assert trace["regional_hit"] == "Lebanon"

    @pytest.mark.asyncio
    async def test_detects_north_iran(self, trace_engine):
        trace = await trace_engine.trace_cluster_origin(NORTH_IRAN_CITIES, allow_strategic=True)
        assert trace["method"] == "strategic_projection"
        assert trace["origin"] == "Iran"
        assert trace["strategic_hit"] == "North Iran"

    @pytest.mark.asyncio
    async def test_detects_yemen(self, trace_engine):
        trace = await trace_engine.trace_cluster_origin(YEMEN_CITIES, allow_strategic=True)
        assert trace["method"] == "strategic_projection"
        assert trace["origin"] == "Yemen"
        assert trace["strategic_hit"] == "Yemen"

    @pytest.mark.asyncio
    async def test_detects_iran_southern_via_projection(self, trace_engine):
        v_lat, v_lon = _unit_vector_to(IRAN_SOUTHERN_TARGET, IRAN_SOUTHERN_CENTROID)
        hit, proj = trace_engine._match_territory_at_projection(
            IRAN_SOUTHERN_CENTROID, v_lat, v_lon, 7, ["North Iran", "Iran", "Yemen"]
        )
        assert hit == "Iran"
        _assert_hit_in_polygon(trace_engine, proj, "Iran", use_tactical=False)

    @pytest.mark.asyncio
    async def test_get_projected_origin_for_each_locked_origin(self, trace_engine):
        tactical_polys = {
            "Gaza": "Gaza",
            "Lebanon": "Lebanon",
            "North Iran": "Iran",
            "Yemen": "Yemen",
        }
        cases = [
            ("Gaza", GAZA_CITIES),
            ("Lebanon", LEBANON_CITIES),
            ("North Iran", NORTH_IRAN_CITIES),
            ("Yemen", YEMEN_CITIES),
        ]
        for origin_name, cities in cases:
            proj = trace_engine.get_projected_origin(
                cities, origin_name, depth=trace_engine._projection_max_depth(origin_name, None)
            )
            _assert_hit_in_polygon(trace_engine, proj, tactical_polys[origin_name])

        v_lat, v_lon = _unit_vector_to(IRAN_SOUTHERN_TARGET, IRAN_SOUTHERN_CENTROID)
        hit, _ = trace_engine._ray_march_calc_entry(
            IRAN_SOUTHERN_CENTROID, v_lat, v_lon, "Iran", 16.0
        )
        assert hit is not None
        assert trace_engine.is_point_in_polygon(hit, "Iran", use_tactical=False)
