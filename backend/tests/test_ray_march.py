import numpy as np
import pytest
from unittest.mock import MagicMock

from src.core.engine import TrackingEngine

NORTH_CITIES = [
    {"name": "Tiberias", "coords": [32.7951, 35.5309]},
    {"name": "Safed", "coords": [32.9646, 35.4960]},
    {"name": "Kiryat Shmona", "coords": [33.2079, 35.5702]},
]

HAIFA_NORTH = [
    {"name": "Haifa", "coords": [32.7940, 34.9896]},
    {"name": "Nahariya", "coords": [33.0059, 35.0989]},
    {"name": "Karmiel", "coords": [32.9194, 35.3030]},
]

LEBANON_CITIES = NORTH_CITIES

YEMEN_CITIES = [
    {"name": "BeerSheva", "coords": [31.2518, 34.7915]},
    {"name": "Mitzpe Ramon", "coords": [30.6103, 34.8014]},
    {"name": "Eilat", "coords": [29.5577, 34.9519]},
]


def _display_march_depths(engine, cities, origin_name, depth=None):
    """Return depths grid, tac_inside, calc_entry_i, display depth from project_origin_display."""
    centroid = engine._cluster_centroid(cities)
    oriented = engine._oriented_regression_vector(cities, centroid)
    assert oriented is not None
    v_lat, v_lon = oriented
    calc_max = engine._projection_max_depth(origin_name, depth)
    tac_max = engine.tactical_display_max_depth.get(origin_name, calc_max)
    grid_max = max(calc_max, tac_max)
    depths = engine._depth_grid(0.05, grid_max)
    pts = engine._points_on_ray(centroid, v_lat, v_lon, depths)
    calc_inside = engine._calc_origin_inside_mask(pts, origin_name)
    tac_name = engine._tactical_polygon_name(origin_name)
    tac_inside = engine._tactical_inside_mask(pts, tac_name)
    calc_hits = np.flatnonzero(calc_inside)
    calc_entry_i = None
    if calc_hits.size:
        calc_entry_i = engine._deepest_inside_after_entry(
            int(calc_hits[0]), depths, calc_inside, engine.entry_inset, calc_max
        )
    display, calc_entry = engine.project_origin_display(cities, origin_name, depth=depth)
    display_d = None
    if display is not None:
        delta = np.array(display, dtype=float) - np.array(centroid, dtype=float)
        display_d = float(delta[0] * v_lat + delta[1] * v_lon)
    return depths, tac_inside, calc_entry_i, display_d, display, calc_entry


@pytest.fixture
def engine():
    dm = MagicMock()
    dm.city_to_id = {}
    return TrackingEngine(dm, db_manager=None)


class TestRayMarchHelpers:
    def test_depth_grid_uses_ray_step(self, engine):
        depths = engine._depth_grid(0.05, 0.35)
        np.testing.assert_allclose(depths, [0.05, 0.15, 0.25, 0.35])

    def test_deepest_inside_on_ray_removed(self, engine):
        assert not hasattr(engine, "_deepest_inside_on_ray")

    def test_points_on_ray_matrix_shape(self, engine):
        depths = np.array([0.1, 0.2, 0.3])
        pts = engine._points_on_ray([32.0, 35.0], 0.6, 0.8, depths)
        assert pts.shape == (3, 2)
        assert pts[1, 0] == pytest.approx(32.0 + 0.6 * 0.2)
        assert pts[1, 1] == pytest.approx(35.0 + 0.8 * 0.2)


class TestRayMarchEntry:
    def test_iran_inset_pushes_past_border(self, engine):
        cities = HAIFA_NORTH
        centroid = engine._cluster_centroid(cities)
        v_lat, v_lon = engine._oriented_regression_vector(cities, centroid)
        assert v_lat is not None

        orig_inset = engine.entry_inset
        engine.entry_inset = 0.0
        border_only, border_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "North Iran", 16.0
        )
        engine.entry_inset = orig_inset
        inset, inset_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "North Iran", 16.0
        )

        if border_only is None:
            pytest.skip("Ray does not intersect North Iran calc border for fixture")

        assert inset is not None
        assert inset_d >= border_d
        if inset_d > border_d:
            assert engine.get_distance(inset, border_only) > 0.001

    def test_calc_entry_uses_inset_for_iran(self, engine):
        cities = HAIFA_NORTH
        orig_inset = engine.entry_inset
        engine.entry_inset = 0.0
        border_proj = engine.project_calc_entry(cities, "North Iran", depth=16.0)
        engine.entry_inset = orig_inset
        inset_proj = engine.project_calc_entry(cities, "North Iran", depth=16.0)

        centroid = engine._cluster_centroid(cities)
        oriented = engine._oriented_regression_vector(cities, centroid)
        if oriented is None:
            pytest.skip("No regression vector")
        v_lat, v_lon = oriented

        border_hit, _ = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "North Iran", 16.0
        )
        engine.entry_inset = 0.0
        zero_inset_hit, _ = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "North Iran", 16.0
        )
        engine.entry_inset = orig_inset

        if zero_inset_hit is None:
            pytest.skip("Ray does not intersect North Iran calc border for fixture")

        assert border_hit is not None
        assert border_proj is not None and inset_proj is not None
        if engine.get_distance(inset_proj, border_proj) > 0.001:
            along = (
                (inset_proj[0] - centroid[0]) * v_lat
                + (inset_proj[1] - centroid[1]) * v_lon
            )
            border_along = (
                (border_proj[0] - centroid[0]) * v_lat
                + (border_proj[1] - centroid[1]) * v_lon
            )
            assert along >= border_along - 0.01

    def test_display_pin_uses_display_inset(self, engine):
        cities = HAIFA_NORTH
        display, calc_entry = engine.project_origin_display(cities, "North Iran", depth=16.0)
        if display is None or calc_entry is None:
            pytest.skip("Fixture missing calc or display hit")
        assert engine.get_distance(display, calc_entry) > 0.001 or display != calc_entry

    def test_vectorized_mask_finds_first_crossing(self, engine):
        cities = NORTH_CITIES
        centroid = engine._cluster_centroid(cities)
        v_lat, v_lon = engine._oriented_regression_vector(cities, centroid)
        depths = engine._depth_grid(0.05, 16.0)
        pts = engine._points_on_ray(centroid, v_lat, v_lon, depths)
        inside = engine._calc_origin_inside_mask(pts, "Lebanon")
        hits = np.flatnonzero(inside)
        assert hits.size > 0

        hit, hit_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Lebanon", 16.0
        )
        assert hit is not None
        assert hit_d >= float(depths[hits[0]])

        orig_inset = engine.entry_inset
        engine.entry_inset = 0.0
        _, border_d = engine._ray_march_calc_entry(
            centroid, v_lat, v_lon, "Lebanon", 16.0
        )
        engine.entry_inset = orig_inset
        assert border_d == pytest.approx(float(depths[hits[0]]), abs=0.05)


class TestTacticalDisplayPin:
    def test_north_iran_display_inside_silhouette_east_of_calc(self, engine):
        display, calc_entry = engine.project_origin_display(
            HAIFA_NORTH, "North Iran", depth=16.0
        )
        assert display is not None and calc_entry is not None
        assert display != calc_entry
        assert engine.is_point_in_polygon(display, "Iran", use_tactical=True)
        assert display[1] > calc_entry[1] + 1.5

    def test_lebanon_display_inset_not_at_tac_max(self, engine):
        depths, tac_inside, calc_entry_i, display_d, display, calc_entry = (
            _display_march_depths(engine, LEBANON_CITIES, "Lebanon", depth=0.5)
        )
        assert display is not None and calc_entry is not None
        assert engine.is_point_in_polygon(display, "Lebanon", use_tactical=True)

        tac_all = np.flatnonzero(tac_inside)
        tac_after_calc = tac_all[tac_all >= calc_entry_i] if calc_entry_i is not None else tac_all
        tac_entry_i = int(tac_after_calc[0]) if tac_after_calc.size else int(tac_all[0])
        expected_d = float(depths[tac_entry_i]) + engine.display_inset

        assert display_d == pytest.approx(expected_d, abs=engine.ray_step + 0.02)
        assert display_d < float(depths[-1]) - 0.5

    def test_yemen_display_inside_silhouette(self, engine):
        display, calc_entry = engine.project_origin_display(
            YEMEN_CITIES, "Yemen", depth=20.0
        )
        assert display is not None and calc_entry is not None
        assert display != calc_entry
        assert engine.is_point_in_polygon(display, "Yemen", use_tactical=True)

        centroid = engine._cluster_centroid(YEMEN_CITIES)
        v_lat, v_lon = engine._oriented_regression_vector(YEMEN_CITIES, centroid)
        depths = engine._depth_grid(0.05, engine.tactical_display_max_depth["Yemen"])
        pts = engine._points_on_ray(centroid, v_lat, v_lon, depths)
        tac_inside = engine._tactical_inside_mask(pts, "Yemen")
        tac_all = np.flatnonzero(tac_inside)
        if tac_all.size:
            delta = np.array(display, dtype=float) - np.array(centroid, dtype=float)
            display_d = float(delta[0] * v_lat + delta[1] * v_lon)
            calc_max = engine._projection_max_depth("Yemen", 20.0)
            calc_inside = engine._calc_origin_inside_mask(pts, "Yemen")
            calc_hits = np.flatnonzero(calc_inside)
            calc_entry_i = engine._deepest_inside_after_entry(
                int(calc_hits[0]), depths, calc_inside, engine.entry_inset, calc_max
            )
            tac_after_calc = tac_all[tac_all >= calc_entry_i]
            tac_entry_i = int(tac_after_calc[0]) if tac_after_calc.size else int(tac_all[0])
            expected_d = float(depths[tac_entry_i]) + engine.display_inset
            assert display_d == pytest.approx(expected_d, abs=engine.ray_step + 0.02)

    def test_tactical_miss_uses_country_fallback(self, engine):
        engine.boundaries["Gaza"] = []
        cities = [
            {"name": "Ofakim", "coords": [31.3149, 34.6203]},
            {"name": "BeerSheva", "coords": [31.2518, 34.7915]},
        ]
        display, calc_entry = engine.project_origin_display(cities, "Gaza", depth=0.5)
        assert calc_entry is not None
        assert display == engine._tactical_fallback_pin("Gaza")
