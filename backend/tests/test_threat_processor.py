from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.threat_processor import ThreatProcessor
from src.utils.text_utils import standardize_name


class TestThreatProcessorProcess:
    @pytest.fixture
    def processor(self):
        engine = MagicMock()
        engine.get_inflated_hull.return_value = [[0, 0], [1, 1]]
        return ThreatProcessor(engine)

    @pytest.mark.asyncio
    async def test_should_return_none_for_unknown_alert_type(self, processor):
        result = await processor.process("unknownCategory", [])
        assert result is None


class TestThreatProcessorBuildUnifiedCluster:
    @pytest.fixture
    def processor(self):
        engine = MagicMock()
        engine.get_inflated_hull.return_value = [[32.0, 34.0], [32.1, 34.1]]
        return ThreatProcessor(engine)

    def test_should_return_zero_centroid_and_empty_hull_when_no_cities(self, processor):
        centroid, hull = processor._build_unified_cluster([])
        assert centroid == [0, 0]
        assert hull == []

    def test_should_delegate_hull_to_engine_when_cities_present(self, processor):
        cities = [{"name": "A", "coords": [32.0, 34.0]}]
        centroid, hull = processor._build_unified_cluster(cities)
        assert centroid == [32.0, 34.0]
        assert hull == [[32.0, 34.0], [32.1, 34.1]]
        processor.engine.get_inflated_hull.assert_called_once()


class TestThreatProcessorMissileOrigins:
    @pytest.mark.asyncio
    async def test_should_keep_lebanon_origin_when_strategic_mode_is_enabled(self):
        engine = MagicMock()
        engine.get_inflated_hull.return_value = [[0, 0], [1, 1]]
        engine.cluster.return_value = [
            {"cities": [{"name": "NorthCity", "coords": [33.3, 35.6]}], "centroid": [33.3, 35.6]}
        ]
        engine.get_origin = AsyncMock(return_value=("Lebanon", 0.5))
        engine.project_origin_display.return_value = ([33.6, 35.2], [33.5, 35.3])
        engine.origins = {"Lebanon": [33.9, 35.7]}
        engine.strategic_depths = {"Iran": 16.0}
        engine.zoom_levels = {"Lebanon": 8}

        processor = ThreatProcessor(engine)
        processor._map_cities = MagicMock(return_value=[{"name": "NorthCity", "coords": [33.3, 35.6]}])

        active_events = {
            "nf-1": {
                "category": "newsFlash",
                "end_time": None,
                "data": {"all_cities": [{"name": "NorthCity", "coords": [33.3, 35.6]}]},
            }
        }
        result = await processor.process(
            "missiles",
            ["NorthCity"],
            active_events=active_events,
            has_newsflash_in_batch=True,
        )

        assert result is not None
        assert result["clusters"][0]["origin"] == "Lebanon"
        assert result["trajectories"][0]["origin"] == "Lebanon"
        engine.get_origin.assert_awaited_once()
        assert engine.get_origin.await_args.kwargs["allow_strategic"] is True


class TestThreatProcessorMapCities:
    def test_should_include_city_boundary_geometry_when_available(self):
        engine = MagicMock()
        std_name = standardize_name("North City")
        engine.dm.city_map = {
            std_name: {"lat": 33.3, "lon": 35.6, "area": "North", "name": "North City"},
        }
        engine.dm.city_to_id = {std_name: 101}
        engine.city_polygons = {"101": [[33.31, 35.61], [33.32, 35.62], [33.30, 35.63]]}

        processor = ThreatProcessor(engine)
        mapped = processor._map_cities(["North City"])

        assert len(mapped) == 1
        assert mapped[0]["name"] == "North City"
        assert mapped[0]["city_id"] == 101
        assert mapped[0]["boundary"] == [[33.31, 35.61], [33.32, 35.62], [33.30, 35.63]]

    def test_should_fallback_to_none_when_city_id_mapping_missing(self):
        engine = MagicMock()
        std_name = standardize_name("North City")
        engine.dm.city_map = {
            std_name: {"lat": 33.3, "lon": 35.6, "area": "North", "name": "North City"},
        }
        engine.dm.city_to_id = {}
        engine.city_polygons = {"101": [[33.31, 35.61], [33.32, 35.62], [33.30, 35.63]]}

        processor = ThreatProcessor(engine)
        mapped = processor._map_cities(["North City"])

        assert len(mapped) == 1
        assert set(mapped[0].keys()) == {"name", "coords", "area", "city_id", "boundary"}
        assert mapped[0]["city_id"] is None
        assert mapped[0]["boundary"] is None

    def test_should_keep_city_id_and_fallback_boundary_none_when_polygon_missing(self):
        engine = MagicMock()
        std_name = standardize_name("North City")
        engine.dm.city_map = {
            std_name: {"lat": 33.3, "lon": 35.6, "area": "North", "name": "North City"},
        }
        engine.dm.city_to_id = {std_name: 101}
        engine.city_polygons = {}

        processor = ThreatProcessor(engine)
        mapped = processor._map_cities(["North City"])

        assert len(mapped) == 1
        assert set(mapped[0].keys()) == {"name", "coords", "area", "city_id", "boundary"}
        assert mapped[0]["city_id"] == 101
        assert mapped[0]["boundary"] is None
