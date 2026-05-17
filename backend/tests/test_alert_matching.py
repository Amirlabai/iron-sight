"""Comprehensive unit tests for src/utils/alert_matching.py.

Covers: clamp_radius_km, get_event_target_points, matches_alert_scope,
        build_alert_notify_key, format_push_body, and the private
        helpers _haversine_km / _point_in_polygon (tested indirectly
        where private, directly where useful).
"""

import json
import math
from pathlib import Path

import pytest

from src.utils.alert_matching import (
    ALLOWED_SCOPES,
    DEFAULT_RADIUS_KM,
    EXACT_MATCH_KM,
    RADIUS_MAX_KM,
    RADIUS_MIN_KM,
    _cluster_hulls,
    _haversine_km,
    _point_in_polygon,
    build_alert_notify_key,
    clamp_radius_km,
    format_push_body,
    get_event_target_points,
    matches_alert_scope,
)

VECTORS_PATH = Path(__file__).resolve().parents[2] / "shared" / "alert_matching_vectors.json"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vectors():
    with open(VECTORS_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Vector-driven tests (data contract with shared/alert_matching_vectors.json)
# ---------------------------------------------------------------------------


class TestVectors:
    def test_matches_from_vectors(self, vectors):
        for case in vectors["matches"]:
            result = matches_alert_scope(
                case["user"],
                case["event"],
                case["scope"],
                case.get("radiusKm", 10),
            )
            assert result == case["expect"], f"failed vector id={case['id']}"

    def test_notify_keys_from_vectors(self, vectors):
        for case in vectors["notifyKeys"]:
            assert build_alert_notify_key(case["event"]) == case["expect"], case["id"]

    def test_clamp_radius_from_vectors(self, vectors):
        for case in vectors["clampRadius"]:
            assert clamp_radius_km(case["input"]) == case["expect"]


# ---------------------------------------------------------------------------
# clamp_radius_km
# ---------------------------------------------------------------------------


class TestClampRadiusKm:
    def test_should_return_min_when_value_below_minimum(self):
        assert clamp_radius_km(1) == RADIUS_MIN_KM

    def test_should_return_max_when_value_above_maximum(self):
        assert clamp_radius_km(99) == RADIUS_MAX_KM

    def test_should_return_value_unchanged_when_within_range(self):
        assert clamp_radius_km(10) == 10.0

    def test_should_return_min_when_value_is_zero(self):
        assert clamp_radius_km(0) == RADIUS_MIN_KM

    def test_should_return_min_when_value_is_negative(self):
        assert clamp_radius_km(-50) == RADIUS_MIN_KM

    def test_should_return_min_when_value_is_exactly_minimum(self):
        assert clamp_radius_km(RADIUS_MIN_KM) == RADIUS_MIN_KM

    def test_should_return_max_when_value_is_exactly_maximum(self):
        assert clamp_radius_km(RADIUS_MAX_KM) == RADIUS_MAX_KM

    def test_should_return_default_when_value_is_none(self):
        assert clamp_radius_km(None) == DEFAULT_RADIUS_KM

    def test_should_return_default_when_value_is_non_numeric_string(self):
        assert clamp_radius_km("abc") == DEFAULT_RADIUS_KM

    def test_should_parse_numeric_string(self):
        assert clamp_radius_km("20") == 20.0

    def test_should_return_min_when_numeric_string_is_below_minimum(self):
        assert clamp_radius_km("1") == RADIUS_MIN_KM

    def test_should_return_float_for_float_input(self):
        result = clamp_radius_km(15.5)
        assert result == 15.5
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# _haversine_km  (private — imported directly for precision tests)
# ---------------------------------------------------------------------------


class TestHaversineKm:
    def test_should_return_zero_for_identical_points(self):
        assert _haversine_km([32.0, 34.0], [32.0, 34.0]) == pytest.approx(0.0)

    def test_should_return_correct_distance_for_known_points(self):
        # Approximate straight-line Tel Aviv to Jerusalem ≈ 54 km
        tel_aviv = [32.0853, 34.7818]
        jerusalem = [31.7683, 35.2137]
        dist = _haversine_km(tel_aviv, jerusalem)
        assert 50 < dist < 60

    def test_should_be_symmetric(self):
        p1, p2 = [32.0, 34.0], [33.0, 35.0]
        assert _haversine_km(p1, p2) == pytest.approx(_haversine_km(p2, p1))

    def test_should_return_positive_distance_for_different_points(self):
        assert _haversine_km([0.0, 0.0], [1.0, 1.0]) > 0

    def test_should_return_approx_111km_for_one_degree_latitude(self):
        dist = _haversine_km([0.0, 0.0], [1.0, 0.0])
        assert dist == pytest.approx(111.195, rel=0.01)


# ---------------------------------------------------------------------------
# _point_in_polygon
# ---------------------------------------------------------------------------


class TestPointInPolygon:
    _square = [[31.9, 33.9], [31.9, 34.1], [32.1, 34.1], [32.1, 33.9]]

    def test_should_return_true_when_point_is_inside_polygon(self):
        assert _point_in_polygon([32.0, 34.0], self._square) is True

    def test_should_return_false_when_point_is_outside_polygon(self):
        assert _point_in_polygon([29.0, 30.0], self._square) is False

    def test_should_return_false_when_polygon_is_empty(self):
        assert _point_in_polygon([32.0, 34.0], []) is False

    def test_should_return_false_when_polygon_has_fewer_than_three_vertices(self):
        assert _point_in_polygon([32.0, 34.0], [[31.9, 33.9], [32.1, 34.1]]) is False

    def test_should_return_false_when_polygon_is_none(self):
        assert _point_in_polygon([32.0, 34.0], None) is False

    def test_should_return_false_when_point_is_at_corner_outside(self):
        assert _point_in_polygon([31.8, 33.8], self._square) is False


# ---------------------------------------------------------------------------
# get_event_target_points
# ---------------------------------------------------------------------------


class TestGetEventTargetPoints:
    def test_should_return_empty_list_when_event_is_none(self):
        assert get_event_target_points(None) == []

    def test_should_return_empty_list_when_event_is_empty_dict(self):
        assert get_event_target_points({}) == []

    def test_should_collect_coords_from_all_cities(self):
        event = {"all_cities": [{"coords": [32.0, 34.0]}, {"coords": [33.0, 35.0]}]}
        points = get_event_target_points(event)
        assert [32.0, 34.0] in points
        assert [33.0, 35.0] in points

    def test_should_collect_hull_vertices_from_clusters(self):
        hull = [[31.9, 33.9], [31.9, 34.1], [32.1, 34.1], [32.1, 33.9]]
        event = {"clusters": [{"hull": hull, "cities": []}]}
        points = get_event_target_points(event)
        for vertex in hull:
            assert vertex in points

    def test_should_collect_centroid_from_cluster(self):
        event = {"clusters": [{"cities": [], "centroid": [32.0, 34.0]}]}
        points = get_event_target_points(event)
        assert [32.0, 34.0] in points

    def test_should_deduplicate_identical_coords(self):
        event = {
            "all_cities": [{"coords": [32.0, 34.0]}, {"coords": [32.0, 34.0]}]
        }
        points = get_event_target_points(event)
        assert points.count([32.0, 34.0]) == 1

    def test_should_skip_city_entries_without_coords(self):
        event = {"all_cities": [{"name": "Unknown"}, {"coords": [32.0, 34.0]}]}
        points = get_event_target_points(event)
        assert len(points) == 1

    def test_should_skip_city_entries_that_are_not_dicts(self):
        event = {"all_cities": ["string_entry", {"coords": [32.0, 34.0]}]}
        points = get_event_target_points(event)
        assert len(points) == 1

    def test_should_skip_hull_with_fewer_than_two_vertices(self):
        event = {"clusters": [{"hull": [[32.0, 34.0]], "cities": []}]}
        points = get_event_target_points(event)
        assert points == []

    def test_should_collect_cities_from_cluster_cities_list(self):
        event = {
            "clusters": [{"cities": [{"coords": [32.5, 34.5]}], "hull": None}],
            "all_cities": [],
        }
        points = get_event_target_points(event)
        assert [32.5, 34.5] in points


# ---------------------------------------------------------------------------
# matches_alert_scope — scope "all"
# ---------------------------------------------------------------------------


class TestMatchesAlertScopeAll:
    _event = {"id": "e1", "category": "missiles", "all_cities": [{"coords": [32.0, 34.0]}]}

    def test_should_return_true_when_scope_is_all(self):
        assert matches_alert_scope(None, self._event, "all") is True

    def test_should_return_true_when_scope_is_all_regardless_of_user_location(self):
        assert matches_alert_scope([29.0, 34.0], self._event, "all") is True

    def test_should_return_false_when_event_is_none(self):
        assert matches_alert_scope(None, None, "all") is False

    def test_should_return_false_when_category_is_newsflash(self):
        event = {"id": "nf", "category": "newsFlash", "all_cities": []}
        assert matches_alert_scope([32.0, 34.0], event, "all") is False

    def test_should_return_false_for_unknown_scope(self):
        assert matches_alert_scope([32.0, 34.0], self._event, "unknown_scope") is False


# ---------------------------------------------------------------------------
# matches_alert_scope — scope "radius"
# ---------------------------------------------------------------------------


class TestMatchesAlertScopeRadius:
    _tel_aviv = [32.0853, 34.7818]
    _event_near = {
        "id": "near",
        "category": "missiles",
        "all_cities": [{"coords": [32.0853, 34.7818]}],
    }
    _event_far = {
        "id": "far",
        "category": "missiles",
        "all_cities": [{"coords": [32.0853, 34.7818]}],
    }

    def test_should_return_true_when_user_is_within_radius(self):
        assert matches_alert_scope(self._tel_aviv, self._event_near, "radius", 15) is True

    def test_should_return_false_when_user_is_outside_radius(self):
        eilat = [29.55, 34.95]
        assert matches_alert_scope(eilat, self._event_far, "radius", 5) is False

    def test_should_return_false_when_user_location_is_none(self):
        assert matches_alert_scope(None, self._event_near, "radius", 15) is False

    def test_should_return_false_when_user_location_is_empty(self):
        assert matches_alert_scope([], self._event_near, "radius", 15) is False

    def test_should_return_false_when_event_has_no_target_points(self):
        event = {"id": "empty", "category": "missiles", "all_cities": []}
        assert matches_alert_scope(self._tel_aviv, event, "radius", 15) is False

    def test_should_use_default_radius_when_radius_km_is_none(self):
        # User co-located with city: should match with any non-trivial radius
        assert matches_alert_scope(self._tel_aviv, self._event_near, "radius", None) is True

    def test_should_return_false_when_category_is_newsflash(self):
        event = {"id": "nf", "category": "newsFlash", "all_cities": [{"coords": [32.0853, 34.7818]}]}
        assert matches_alert_scope(self._tel_aviv, event, "radius", 15) is False

    def test_should_match_when_any_city_is_within_radius(self):
        event = {
            "id": "multi",
            "category": "missiles",
            "all_cities": [
                {"coords": [29.55, 34.95]},   # far
                {"coords": [32.0853, 34.7818]},  # near
            ],
        }
        assert matches_alert_scope(self._tel_aviv, event, "radius", 5) is True


# ---------------------------------------------------------------------------
# matches_alert_scope — scope "exact"
# ---------------------------------------------------------------------------


class TestMatchesAlertScopeExact:
    _inside_hull_user = [32.0, 34.0]
    _square_hull = [[31.9, 33.9], [31.9, 34.1], [32.1, 34.1], [32.1, 33.9]]

    def test_should_return_true_when_user_is_inside_hull(self):
        event = {
            "id": "e1",
            "category": "missiles",
            "clusters": [{"hull": self._square_hull, "cities": []}],
            "all_cities": [],
        }
        assert matches_alert_scope(self._inside_hull_user, event, "exact") is True

    def test_should_return_false_when_user_is_outside_hull(self):
        outside_user = [29.0, 30.0]
        event = {
            "id": "e2",
            "category": "missiles",
            "clusters": [{"hull": self._square_hull, "cities": []}],
            "all_cities": [],
        }
        assert matches_alert_scope(outside_user, event, "exact") is False

    def test_should_return_true_when_user_is_within_1km_of_city(self):
        tel_aviv = [32.0853, 34.7818]
        event = {
            "id": "e3",
            "category": "missiles",
            "all_cities": [{"coords": [32.0853, 34.7818]}],
        }
        assert matches_alert_scope(tel_aviv, event, "exact") is True

    def test_should_return_false_when_user_is_more_than_1km_from_all_cities(self):
        # Eilat is well over 1 km from Tel Aviv
        eilat = [29.55, 34.95]
        event = {
            "id": "e4",
            "category": "missiles",
            "all_cities": [{"coords": [32.0853, 34.7818]}],
        }
        assert matches_alert_scope(eilat, event, "exact") is False

    def test_should_return_false_when_event_has_no_hulls_and_no_cities(self):
        event = {"id": "e5", "category": "missiles", "all_cities": [], "clusters": []}
        assert matches_alert_scope(self._inside_hull_user, event, "exact") is False

    def test_should_return_false_when_user_location_is_none(self):
        event = {
            "id": "e6",
            "category": "missiles",
            "all_cities": [{"coords": [32.0853, 34.7818]}],
        }
        assert matches_alert_scope(None, event, "exact") is False

    def test_should_match_city_in_cluster_cities_list_for_exact_scope(self):
        tel_aviv = [32.0853, 34.7818]
        event = {
            "id": "e7",
            "category": "missiles",
            "clusters": [
                {"hull": None, "cities": [{"coords": [32.0853, 34.7818]}]}
            ],
            "all_cities": [],
        }
        assert matches_alert_scope(tel_aviv, event, "exact") is True

    def test_should_ignore_hull_with_fewer_than_three_points_for_exact_scope(self):
        # A degenerate hull (line) must not be used for polygon check
        event = {
            "id": "e8",
            "category": "missiles",
            "clusters": [
                {"hull": [[32.0, 34.0], [32.1, 34.1]], "cities": []}
            ],
            "all_cities": [],
        }
        assert matches_alert_scope([32.05, 34.05], event, "exact") is False


# ---------------------------------------------------------------------------
# build_alert_notify_key
# ---------------------------------------------------------------------------


class TestBuildAlertNotifyKey:
    def test_should_include_event_id_and_city_count(self):
        event = {"id": "abc", "all_cities": [{}, {}, {}]}
        assert build_alert_notify_key(event) == "abc:3"

    def test_should_return_unknown_when_id_is_missing(self):
        event = {"all_cities": [{}]}
        assert build_alert_notify_key(event) == "unknown:1"

    def test_should_return_zero_city_count_when_all_cities_is_empty(self):
        event = {"id": "x", "all_cities": []}
        assert build_alert_notify_key(event) == "x:0"

    def test_should_return_zero_city_count_when_all_cities_is_missing(self):
        event = {"id": "y"}
        assert build_alert_notify_key(event) == "y:0"

    def test_should_return_zero_city_count_when_all_cities_is_none(self):
        event = {"id": "z", "all_cities": None}
        assert build_alert_notify_key(event) == "z:0"

    def test_should_produce_unique_keys_for_different_city_counts(self):
        event_a = {"id": "q", "all_cities": [{}]}
        event_b = {"id": "q", "all_cities": [{}, {}]}
        assert build_alert_notify_key(event_a) != build_alert_notify_key(event_b)


# ---------------------------------------------------------------------------
# format_push_body
# ---------------------------------------------------------------------------


class TestFormatPushBody:
    def test_should_return_fallback_when_no_cities(self):
        assert format_push_body({"all_cities": []}) == "Active threat detected"

    def test_should_return_fallback_when_all_cities_is_missing(self):
        assert format_push_body({}) == "Active threat detected"

    def test_should_return_fallback_when_all_cities_is_none(self):
        assert format_push_body({"all_cities": None}) == "Active threat detected"

    def test_should_return_city_name_for_single_city(self):
        event = {"all_cities": [{"name": "Tel Aviv"}]}
        assert format_push_body(event) == "Tel Aviv"

    def test_should_join_multiple_city_names(self):
        event = {"all_cities": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
        assert format_push_body(event) == "A, B, C"

    def test_should_cap_at_four_names_and_append_extra_count(self):
        event = {
            "all_cities": [
                {"name": "A"},
                {"name": "B"},
                {"name": "C"},
                {"name": "D"},
                {"name": "E"},
                {"name": "F"},
            ]
        }
        body = format_push_body(event)
        assert body == "A, B, C, D (+2)"

    def test_should_include_string_city_entries(self):
        event = {"all_cities": ["Tel Aviv", "Haifa"]}
        assert format_push_body(event) == "Tel Aviv, Haifa"

    def test_should_append_extra_for_unnamed_dict_entries(self):
        # extra = len(cities) - len(names_collected), so unnamed entries count toward extra
        event = {"all_cities": [{"coords": [32.0, 34.0]}, {"name": "Haifa"}]}
        assert format_push_body(event) == "Haifa (+1)"

    def test_should_handle_exactly_four_cities_without_extra_suffix(self):
        event = {
            "all_cities": [
                {"name": "A"},
                {"name": "B"},
                {"name": "C"},
                {"name": "D"},
            ]
        }
        body = format_push_body(event)
        assert body == "A, B, C, D"
        assert "(+" not in body

    def test_should_append_extra_count_even_when_all_cities_are_unnamed(self):
        # extra = len(cities) - 0 = 5; fallback body gains the suffix
        event = {"all_cities": [{}, {}, {}, {}, {}]}
        assert format_push_body(event) == "Active threat detected (+5)"


# ---------------------------------------------------------------------------
# ALLOWED_SCOPES constant
# ---------------------------------------------------------------------------


class TestAllowedScopes:
    def test_should_contain_all_scope(self):
        assert "all" in ALLOWED_SCOPES

    def test_should_contain_radius_scope(self):
        assert "radius" in ALLOWED_SCOPES

    def test_should_contain_exact_scope(self):
        assert "exact" in ALLOWED_SCOPES

    def test_should_not_contain_invalid_scope(self):
        assert "invalid" not in ALLOWED_SCOPES

    def test_should_have_exactly_three_entries(self):
        assert len(ALLOWED_SCOPES) == 3
