from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.missile_origins import apply_large_salvo_iran_policy, build_missile_origins


def _engine_with_depths():
    eng = MagicMock()
    eng.strategic_depths = {"Iran": 7.0, "Yemen": 7.0}
    eng.zoom_levels = {"Yemen": 5, "Iran": 6}
    return eng


class TestApplyLargeSalvoIranPolicy:
    def test_force_iran_overrides_ambiguous_origin(self):
        eng = _engine_with_depths()
        org, depth = apply_large_salvo_iran_policy("North Iran", 6.0, True, eng)
        assert org == "Iran"
        assert depth == 7.0

    def test_force_iran_skips_when_geometry_is_yemen(self):
        eng = _engine_with_depths()
        org, depth = apply_large_salvo_iran_policy("Yemen", 7.0, True, eng)
        assert org == "Yemen"
        assert depth == 7.0

    def test_no_force_leaves_origin_unchanged(self):
        eng = _engine_with_depths()
        org, depth = apply_large_salvo_iran_policy("Iran", 6.0, False, eng)
        assert org == "Iran"
        assert depth == 6.0


class TestBuildMissileOriginsForceIran:
    @pytest.mark.asyncio
    async def test_yemen_trace_not_overridden_by_force_iran(self):
        eng = _engine_with_depths()
        eng.get_origin = AsyncMock(return_value=("Yemen", 7.0))
        eng.project_origin_display = MagicMock(return_value=([15.0, 44.0], None))
        eng.cluster = MagicMock(
            return_value=[{"centroid": [31.0, 35.0], "cities": [{"name": "A", "coords": [31.0, 35.0]}]}]
        )

        result = await build_missile_origins(
            eng,
            eng.cluster.return_value,
            [{"name": "A", "coords": [31.0, 35.0]}],
            allow_strategic=True,
            force_iran=True,
            hull_for_cities=lambda cities: [],
        )

        assert result["clusters"][0]["origin"] == "Yemen"
        assert result["title"] == "Yemen Salvo"
