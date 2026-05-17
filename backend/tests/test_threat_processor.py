from unittest.mock import MagicMock

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
