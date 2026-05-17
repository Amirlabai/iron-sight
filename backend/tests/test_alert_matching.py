import json
from pathlib import Path

import pytest

from src.utils.alert_matching import (
    matches_alert_scope,
    build_alert_notify_key,
    clamp_radius_km,
    ALLOWED_SCOPES,
)

VECTORS_PATH = Path(__file__).resolve().parents[2] / "shared" / "alert_matching_vectors.json"


@pytest.fixture
def vectors():
    with open(VECTORS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_matches_from_vectors(vectors):
    for case in vectors["matches"]:
        user = case["user"]
        prefs_scope = case["scope"]
        radius = case.get("radiusKm", 10)
        result = matches_alert_scope(user, case["event"], prefs_scope, radius)
        assert result == case["expect"], case["id"]


def test_notify_keys_from_vectors(vectors):
    for case in vectors["notifyKeys"]:
        assert build_alert_notify_key(case["event"]) == case["expect"], case["id"]


def test_clamp_radius_from_vectors(vectors):
    for case in vectors["clampRadius"]:
        assert clamp_radius_km(case["input"]) == case["expect"]


def test_allowed_scopes():
    assert "all" in ALLOWED_SCOPES
    assert "invalid" not in ALLOWED_SCOPES
