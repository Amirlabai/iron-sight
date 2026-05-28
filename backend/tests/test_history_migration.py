import importlib.util
from pathlib import Path

from src.utils.text_utils import standardize_name

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_history_city_bounds.py"
spec = importlib.util.spec_from_file_location("history_backfill", SCRIPT_PATH)
history_backfill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history_backfill)


class TestHistoryMigrationEnrichment:
    def test_should_enrich_all_cities_and_cluster_cities(self):
        doc = {
            "all_cities": [{"name": "North City", "coords": [33.3, 35.6]}],
            "clusters": [{"cities": [{"name": "North City", "coords": [33.3, 35.6]}]}],
        }
        city_to_id = {standardize_name("North City"): 101}
        city_polygons = {"101": [[33.1, 35.1], [33.2, 35.2], [33.3, 35.3]]}

        changed = history_backfill.enrich_document(doc, city_to_id, city_polygons)

        assert changed is True
        assert doc["all_cities"][0]["city_id"] == 101
        assert doc["all_cities"][0]["boundary"] == city_polygons["101"]
        assert doc["clusters"][0]["cities"][0]["city_id"] == 101
        assert doc["clusters"][0]["cities"][0]["boundary"] == city_polygons["101"]

    def test_should_set_none_fallback_when_mapping_missing(self):
        doc = {
            "all_cities": [{"name": "Unknown City", "coords": [0, 0], "city_id": 7, "boundary": [[1, 1], [2, 2], [3, 3]]}],
            "clusters": [],
        }
        changed = history_backfill.enrich_document(doc, {}, {})
        assert changed is True
        assert doc["all_cities"][0]["city_id"] is None
        assert doc["all_cities"][0]["boundary"] is None
