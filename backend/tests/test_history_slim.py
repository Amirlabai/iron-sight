import copy

from src.utils.history_slim import slim_history_record


def _fat_archive():
    return {
        "id": "abc123",
        "category": "missiles",
        "title": "Lebanon Salvo",
        "time": "2026-01-01T12:00:00",
        "visual_config": {"color": "#f00"},
        "center": [32.0, 34.0],
        "all_cities": [
            {"name": "Tel Aviv", "area": "מרכז", "coords": [32.1, 34.8], "boundary": [[1, 2], [3, 4]]},
        ],
        "clusters": [{"origin": "Lebanon", "hull": [[0, 0]] * 100, "cities": []}],
        "trajectories": [{"origin": "Lebanon", "origin_coords": [33.0, 35.0], "target_coords": [32.0, 34.0]}],
    }


def test_slim_strips_geometry():
    slim = slim_history_record(_fat_archive())
    assert slim["_listView"] is True
    assert slim["all_cities"] == [{"name": "Tel Aviv", "area": "מרכז"}]
    assert slim["trajectories"] == [{
        "origin": "Lebanon",
        "origin_coords": [33.0, 35.0],
    }]
    assert slim["clusters"] == [{"origin": "Lebanon", "cities": []}]
    assert "hull" not in str(slim)


def test_slim_preserves_origin_for_filter():
    slim = slim_history_record(_fat_archive())
    assert slim["trajectories"][0]["origin"] == "Lebanon"


def test_slim_does_not_mutate_source():
    src = _fat_archive()
    orig = copy.deepcopy(src)
    slim_history_record(src)
    assert src == orig
