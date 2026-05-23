#!/usr/bin/env python3
"""Merge il(2).json outer ring + ps.json holes into Israel Feature in countries geodata."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IL_PATH = ROOT / ".incoming" / "il(2).json"
PS_PATH = ROOT / ".incoming" / "ps.json"
DASHBOARD_COUNTRIES = ROOT / "dashboard" / "src" / "assets" / "countries.json"
BACKEND_GEOJSON = ROOT / "backend" / "src" / "data" / "countries.geojson"


def load_rings() -> list[list[list[float]]]:
    with open(IL_PATH, encoding="utf-8") as f:
        il = json.load(f)
    with open(PS_PATH, encoding="utf-8") as f:
        ps = json.load(f)

    outer = il["features"][0]["geometry"]["coordinates"][0]
    holes = [feat["geometry"]["coordinates"][0] for feat in ps["features"]]
    return [outer, *holes]


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

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")

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
