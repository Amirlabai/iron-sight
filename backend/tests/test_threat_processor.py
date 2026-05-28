from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.threat_processor import ThreatProcessor


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
        engine.get_projected_origin.return_value = [33.6, 35.2]
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
