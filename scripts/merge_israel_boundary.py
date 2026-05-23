#!/usr/bin/env python3
"""Merge il(2).json outer ring + ps.json holes into Israel Feature in countries geodata.

Writes dashboard/src/assets/countries.json and backend/src/data/countries.geojson
in one run; keep both in sync (compare file hashes in CI if needed).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IL_PATH = ROOT / ".incoming" / "il(2).json"
PS_PATH = ROOT / ".incoming" / "ps.json"
DASHBOARD_COUNTRIES = ROOT / "dashboard" / "src" / "assets" / "countries.json"
BACKEND_GEOJSON = ROOT / "backend" / "src" / "data" / "countries.geojson"


def ring_signed_area_lonlat(ring: list[list[float]]) -> float:
    """Shoelace signed area; positive => CCW outer, negative => CW hole (GeoJSON)."""
    area = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def validate_ring_winding(rings: list[list[list[float]]]) -> None:
    if not rings:
        raise ValueError("No rings to validate")
    outer_area = ring_signed_area_lonlat(rings[0])
    if outer_area <= 0:
        raise ValueError(
            "Outer ring must be counter-clockwise (CCW); got signed area "
            f"{outer_area:.6f}"
        )
    for i, hole in enumerate(rings[1:], start=1):
        hole_area = ring_signed_area_lonlat(hole)
        if hole_area >= 0:
            raise ValueError(
                f"Hole ring {i} must be clockwise (CW); got signed area {hole_area:.6f}"
            )


def load_rings() -> list[list[list[float]]]:
    with open(IL_PATH, encoding="utf-8") as f:
        il = json.load(f)
    with open(PS_PATH, encoding="utf-8") as f:
        ps = json.load(f)

    outer = il["features"][0]["geometry"]["coordinates"][0]
    holes = [feat["geometry"]["coordinates"][0] for feat in ps["features"]]
    rings = [outer, *holes]
    validate_ring_winding(rings)
    return rings


def atomic_json_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def patch_feature_collection(path: Path, rings: list[list[list[float]]], props: dict) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    updated = False
    for i, feat in enumerate(features):
        if feat.get("properties", {}).get("location") == "Israel":
            features[i] = {
                "type": "Feature",
                "properties": dict(props),
                "geometry": {"type": "Polygon", "coordinates": rings},
            }
            updated = True
            break

    if not updated:
        raise ValueError(f"No Israel feature in {path}")

    atomic_json_write(path, data)
    print(f"Updated {path} ({len(rings)} rings: 1 outer + {len(rings) - 1} holes)")


def main() -> None:
    if not IL_PATH.exists() or not PS_PATH.exists():
        raise SystemExit(f"Missing source files: {IL_PATH} or {PS_PATH}")

    rings = load_rings()
    with open(DASHBOARD_COUNTRIES, encoding="utf-8") as f:
        dashboard = json.load(f)

    israel_props = None
    for feat in dashboard["features"]:
        if feat.get("properties", {}).get("location") == "Israel":
            israel_props = feat["properties"]
            break
    if not israel_props:
        raise SystemExit("Israel feature not found in dashboard countries.json")

    patch_feature_collection(DASHBOARD_COUNTRIES, rings, israel_props)
    patch_feature_collection(BACKEND_GEOJSON, rings, israel_props)


if __name__ == "__main__":
    main()
