import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.origin_ml import (
    resolve_origin_ml,
    score_cities_against_record,
    score_origin_candidate,
    geometric_tiebreak,
    collapse_missile_origins,
    normalize_origin_label,
)


class TestNormalizeOriginLabel:
    def test_north_iran_maps_to_iran(self):
        assert normalize_origin_label("North Iran") == "Iran"


class TestScoreCitiesAgainstRecord:
    def test_exact_city_set_scores_one(self):
        cities = [{"name": "A", "coords": [32.0, 35.0]}]
        record = {
            "all_cities": [{"name": "A", "coords": [32.0, 35.0]}],
            "trajectories": [{"origin": "Lebanon", "depth": 0.5}],
            "center": [32.0, 35.0],
        }
        assert score_cities_against_record(cities, record) == 1.0


class TestResolveOriginMl:
    @pytest.mark.asyncio
    async def test_picks_lebanon_when_verified_corpus_matches(self):
        engine = MagicMock()
        engine.verified_history = [
            {
                "all_cities": [
                    {"name": "טבריה", "coords": [32.79, 35.53]},
                    {"name": "מצפה", "coords": [32.79, 35.51]},
                    {"name": "כפר חיטים", "coords": [32.80, 35.50]},
                ],
                "center": [32.79, 35.51],
                "trajectories": [{"origin": "Lebanon", "depth": 0.5}],
            },
            {
                "all_cities": [{"name": "נתניה", "coords": [32.3, 34.9]}],
                "center": [32.3, 34.9],
                "trajectories": [{"origin": "Iran", "depth": 16.0}],
            },
        ]
        engine._sync_verified_history = AsyncMock()

        cities = [
            {"name": "טבריה", "coords": [32.79, 35.53]},
            {"name": "מצפה", "coords": [32.79, 35.51]},
            {"name": "כפר חיטים", "coords": [32.80, 35.50]},
        ]
        winner, confidence, scores, resolved_by = await resolve_origin_ml(
            engine, cities, ["Iran", "Lebanon"]
        )
        assert winner == "Lebanon"
        assert resolved_by == "ml"
        assert scores["Lebanon"] > scores["Iran"]
        assert confidence > 0

    @pytest.mark.asyncio
    async def test_fallback_when_no_verified_history(self):
        engine = MagicMock()
        engine.verified_history = []
        engine._sync_verified_history = AsyncMock()

        cities = [{"name": "A", "coords": [32.0, 35.0]}]
        winner, _, _, resolved_by = await resolve_origin_ml(
            engine, cities, ["Iran", "Lebanon"]
        )
        assert resolved_by == "geometry_fallback"
        assert winner == "Lebanon"

    @pytest.mark.asyncio
    async def test_requires_two_candidates(self):
        engine = MagicMock()
        with pytest.raises(ValueError):
            await resolve_origin_ml(engine, [], ["Lebanon"])


class TestGeometricTiebreak:
    def test_prefers_lebanon_over_iran(self):
        assert geometric_tiebreak(["Iran", "Lebanon"]) == "Lebanon"


class TestCollapseMissileOrigins:
    def test_single_trajectory_after_collapse(self):
        engine = MagicMock()
        engine.strategic_depths = {"Lebanon": 0.5, "Iran": 16.0}
        engine.origins = {"Lebanon": [33.9, 35.7]}
        engine.zoom_levels = {"Lebanon": 8}
        engine.get_projected_origin = MagicMock(return_value=[33.5, 35.5])

        payload = {
            "clusters": [{"origin": "Iran", "cities": []}],
            "trajectories": [{"origin": "Iran"}, {"origin": "Lebanon"}],
            "all_cities": [{"name": "X", "coords": [32.8, 35.5]}],
        }
        collapse_missile_origins(payload, "Lebanon", 0.9, {"Iran": 0.1, "Lebanon": 0.9}, "ml", engine)
        assert len(payload["trajectories"]) == 1
        assert payload["trajectories"][0]["origin"] == "Lebanon"
        assert payload["title"] == "Lebanon Salvo"
