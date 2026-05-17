import numpy as np
import pytest

from src.utils.cluster_utils import (
    group_events,
    haversine_distance,
    haversine_distance_matrix,
    is_subset,
    recalculate_unified_metadata,
)


class TestHaversineDistance:
    def test_should_return_inf_when_coord1_is_none(self):
        assert haversine_distance(None, [32.0, 34.0]) == float("inf")

    def test_should_return_inf_when_coord2_is_none(self):
        assert haversine_distance([32.0, 34.0], None) == float("inf")

    def test_should_return_zero_for_identical_points(self):
        p = [32.0853, 34.7818]
        assert haversine_distance(p, p) == pytest.approx(0.0)

    def test_should_return_known_distance_between_cities(self):
        tel_aviv = [32.0853, 34.7818]
        jerusalem = [31.7683, 35.2137]
        dist = haversine_distance(tel_aviv, jerusalem)
        assert 50 < dist < 60


class TestHaversineDistanceMatrix:
    def test_should_return_square_matrix_with_correct_shape(self):
        coords = np.array([[32.0, 34.0], [33.0, 35.0], [31.0, 33.0]])
        mat = haversine_distance_matrix(coords)
        assert mat.shape == (3, 3)
        assert np.allclose(np.diag(mat), 0.0)


class TestIsSubset:
    def test_should_return_false_when_either_list_has_no_named_cities(self):
        assert is_subset([{"name": "A"}], [{}]) is False
        assert is_subset([{}], [{"name": "B"}]) is False

    def test_should_return_true_when_names_are_subset(self):
        a = [{"name": "Haifa"}, {"name": "Tel Aviv"}]
        b = [{"name": "Haifa"}, {"name": "Tel Aviv"}, {"name": "Jerusalem"}]
        assert is_subset(a, b) is True

    def test_should_return_false_when_not_subset(self):
        a = [{"name": "Eilat"}]
        b = [{"name": "Haifa"}]
        assert is_subset(a, b) is False


class TestRecalculateUnifiedMetadata:
    def test_should_return_none_tuple_when_cities_empty(self):
        assert recalculate_unified_metadata([]) == (None, None)

    def test_should_return_centroid_and_hull_for_single_city_without_engine(self):
        cities = [{"name": "A", "coords": [32.0, 34.0]}]
        centroid, hull = recalculate_unified_metadata(cities, engine=None)
        assert centroid == [32.0, 34.0]
        assert len(hull) == 4

    def test_should_use_engine_hull_when_engine_provided(self):
        class FakeEngine:
            def get_inflated_hull(self, coords, factor, cities=None):
                return [[0.0, 0.0], [1.0, 1.0]]

        cities = [{"coords": [32.0, 34.0]}, {"coords": [33.0, 35.0]}]
        centroid, hull = recalculate_unified_metadata(cities, engine=FakeEngine())
        assert hull == [[0.0, 0.0], [1.0, 1.0]]


class TestGroupEvents:
    def test_should_return_empty_list_when_active_events_empty(self):
        assert group_events({}) == []

    def test_should_return_single_group_for_one_active_event(self):
        active = {
            "e1": {
                "category": "missiles",
                "end_time": None,
                "data": {
                    "all_cities": [{"name": "A", "coords": [32.0, 34.0], "area": "מרכז"}],
                    "center": [32.0, 34.0],
                },
            }
        }
        groups = group_events(active)
        assert groups == [["e1"]]

    def test_should_exclude_ended_events_when_include_all_false(self):
        active = {
            "ended": {
                "category": "missiles",
                "end_time": "2024-01-01T00:00:00",
                "data": {"all_cities": [], "center": [32.0, 34.0]},
            }
        }
        assert group_events(active) == []

    def test_should_include_ended_events_when_include_all_true(self):
        active = {
            "ended": {
                "category": "missiles",
                "end_time": "2024-01-01T00:00:00",
                "data": {
                    "all_cities": [{"name": "A", "coords": [32.0, 34.0], "area": "מרכז"}],
                    "center": [32.0, 34.0],
                },
            }
        }
        groups = group_events(active, include_all=True)
        assert groups == [["ended"]]
