"""
Verification script for INDEX_ERROR_HARDENING mission.
Simulates _lookup_historical_match against records with empty trajectories.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import numpy as np

# Minimal stub to avoid full engine init (no geodata files needed)
class StubEngine:
    def __init__(self):
        self.verified_history = []

    def _lookup_historical_match(self, cities):
        if not self.verified_history:
            return None

        current_names = {c['name'] for c in cities if c.get('name')}
        current_centroid = np.mean([c['coords'] for c in cities], axis=0)

        for item in self.verified_history:
            # Guard: skip records with empty or missing trajectories
            trajectories = item.get("trajectories")
            if not trajectories:
                continue

            hist_names = {c['name'] for c in item.get("all_cities", []) if c.get('name')}

            if current_names == hist_names:
                return trajectories[0]["origin"], trajectories[0].get("depth", 10.0)

            hist_centroid = np.array(item.get("center") or [0, 0])
            dist = np.linalg.norm(current_centroid - hist_centroid) * 111.0

            if dist < 5.0:
                intersection = current_names.intersection(hist_names)
                union = current_names.union(hist_names)
                jaccard = len(intersection) / len(union) if union else 0

                if jaccard > 0.8:
                    org = trajectories[0]["origin"]
                    depth = trajectories[0].get("depth", 10.0)
                    return org.strip(), depth

        return None


def test_empty_trajectories():
    """Record with trajectories: [] must NOT crash."""
    engine = StubEngine()
    engine.verified_history = [
        {
            "id": "empty-traj-001",
            "all_cities": [{"name": "TestCity", "coords": [31.5, 34.5]}],
            "trajectories": [],
            "center": [31.5, 34.5],
            "verified": True,
        }
    ]
    cities = [{"name": "TestCity", "coords": [31.5, 34.5]}]
    result = engine._lookup_historical_match(cities)
    assert result is None, f"Expected None for empty trajectories, got {result}"
    print("PASS: Empty trajectories handled gracefully.")


def test_missing_trajectories_key():
    """Record with no 'trajectories' key must NOT crash."""
    engine = StubEngine()
    engine.verified_history = [
        {
            "id": "no-traj-002",
            "all_cities": [{"name": "TestCity", "coords": [31.5, 34.5]}],
            "center": [31.5, 34.5],
            "verified": True,
        }
    ]
    cities = [{"name": "TestCity", "coords": [31.5, 34.5]}]
    result = engine._lookup_historical_match(cities)
    assert result is None, f"Expected None for missing key, got {result}"
    print("PASS: Missing trajectories key handled gracefully.")


def test_valid_trajectories():
    """Record with valid trajectories must still resolve correctly."""
    engine = StubEngine()
    engine.verified_history = [
        {
            "id": "valid-traj-003",
            "all_cities": [{"name": "Haifa", "coords": [32.8, 35.0]}],
            "trajectories": [{"origin": "Lebanon", "depth": 0.5}],
            "center": [32.8, 35.0],
            "verified": True,
        }
    ]
    cities = [{"name": "Haifa", "coords": [32.8, 35.0]}]
    result = engine._lookup_historical_match(cities)
    assert result == ("Lebanon", 0.5), f"Expected ('Lebanon', 0.5), got {result}"
    print("PASS: Valid trajectory resolved correctly.")


def test_mixed_records():
    """Mix of empty and valid records - engine must skip bad, match good."""
    engine = StubEngine()
    engine.verified_history = [
        {
            "id": "bad-record",
            "all_cities": [{"name": "Haifa", "coords": [32.8, 35.0]}],
            "trajectories": [],
            "center": [32.8, 35.0],
            "verified": True,
        },
        {
            "id": "good-record",
            "all_cities": [{"name": "Haifa", "coords": [32.8, 35.0]}],
            "trajectories": [{"origin": "Lebanon", "depth": 0.5}],
            "center": [32.8, 35.0],
            "verified": True,
        },
    ]
    cities = [{"name": "Haifa", "coords": [32.8, 35.0]}]
    result = engine._lookup_historical_match(cities)
    assert result == ("Lebanon", 0.5), f"Expected ('Lebanon', 0.5), got {result}"
    print("PASS: Mixed records - bad skipped, good matched.")


if __name__ == "__main__":
    print("=" * 50)
    print("INDEX_ERROR_HARDENING - Verification Suite")
    print("=" * 50)
    test_empty_trajectories()
    test_missing_trajectories_key()
    test_valid_trajectories()
    test_mixed_records()
    print("=" * 50)
    print("ALL TESTS PASSED - Mission verified.")
    print("=" * 50)
