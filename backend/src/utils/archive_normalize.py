"""Normalize legacy missile archive payloads to the current single-trajectory schema."""

import copy
import numpy as np

from src.core.missile_origins import build_missile_origins
from src.utils.config import MAX_IRAN_THRESHOLD, MISSILE_INFLATION_FACTOR


def is_history_fixer_committed(alert):
    return bool(alert.get("verified") or alert.get("manual_origin"))


def _display_origin_name(origin_name):
    return "Iran" if origin_name == "North Iran" else origin_name


def _unique_cities(cities):
    seen = set()
    out = []
    for city in cities or []:
        name = city.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(city)
    return out


def _pick_winner_from_stored(alert, candidates):
    scores = alert.get("origin_ml_scores") or {}
    if scores:
        return max(scores, key=scores.get)
    manual = (alert.get("manual_origin") or "").strip()
    if manual and manual in candidates:
        return manual
    title = (alert.get("title") or "").lower()
    for cand in candidates:
        if _display_origin_name(cand).lower() in title:
            return cand
    trajs = alert.get("trajectories") or []
    if trajs:
        first = (trajs[0].get("origin") or "").strip()
        if first in candidates:
            return first
    return sorted(candidates)[0]


def _merge_clusters_visual(engine, alert, origin):
    """One inflated hull over all cities (avoids legacy per-city circles)."""
    cities = _unique_cities(alert.get("all_cities") or [])
    if not cities:
        return
    coords = np.array([c["coords"] for c in cities])
    cnt = np.mean(coords, axis=0).tolist()
    hull = engine.get_inflated_hull(
        [c["coords"] for c in cities],
        MISSILE_INFLATION_FACTOR,
        cities=cities,
    )
    alert["clusters"] = [{
        "origin": origin,
        "centroid": cnt,
        "cities": cities,
        "hull": hull,
    }]


async def normalize_missile_archive(engine, alert, *, allow_strategic=True):
    """
    Rebuild clusters + a single trajectory for unverified legacy missile rows.
    Returns (alert, changed, change_labels).
    """
    if is_history_fixer_committed(alert):
        return alert, False, []

    cities = _unique_cities(alert.get("all_cities") or [])
    if not cities:
        return alert, False, []

    before = copy.deepcopy({
        "trajectories": alert.get("trajectories"),
        "clusters": alert.get("clusters"),
        "title": alert.get("title"),
        "center": alert.get("center"),
    })

    coords = np.array([c["coords"] for c in cities])
    cnt = np.mean(coords, axis=0).tolist()
    alert["center"] = cnt
    alert["all_cities"] = cities

    total_unique = len({c["name"] for c in cities})
    force_iran = total_unique > MAX_IRAN_THRESHOLD and allow_strategic

    def _archive_ml_resolver(winner, confidence, scores, resolved_by, candidates):
        if resolved_by == "geometry_fallback" and len(candidates) > 1:
            winner = _pick_winner_from_stored(alert, candidates)
            confidence = scores.get(winner, 0.0) if scores else 0.0
            resolved_by = "archive_stored_winner"
        return winner, confidence, resolved_by

    raw_clusters = engine.cluster(cities)
    origin_result = await build_missile_origins(
        engine,
        raw_clusters,
        cities,
        allow_strategic=allow_strategic,
        force_iran=force_iran,
        hull_for_cities=lambda rc_cities: engine.get_inflated_hull(
            [c["coords"] for c in rc_cities],
            MISSILE_INFLATION_FACTOR,
            cities=rc_cities,
        ),
        ml_winner_resolver=_archive_ml_resolver,
    )
    processed_clusters = origin_result["clusters"]
    trajectories = origin_result["trajectories"]
    alert["title"] = origin_result["title"]
    alert["zoom_level"] = origin_result["zoom_level"]
    origin_candidates = origin_result.get("origin_candidates")
    if origin_result.get("origin_ml_scores") is not None:
        alert["origin_ml_scores"] = origin_result["origin_ml_scores"]
    if origin_result.get("origin_resolved_by") is not None:
        alert["origin_resolved_by"] = origin_result["origin_resolved_by"]
    if origin_result.get("origin_ml_confidence") is not None:
        alert["origin_ml_confidence"] = origin_result["origin_ml_confidence"]

    winner_origin = trajectories[0]["origin"] if trajectories else None
    if winner_origin:
        for cluster in processed_clusters:
            cluster["origin"] = winner_origin

    alert["clusters"] = processed_clusters
    alert["trajectories"] = trajectories
    if origin_candidates is not None:
        alert["origin_candidates"] = origin_candidates

    target = trajectories[0].get("target_coords") if trajectories else None
    if target:
        alert["center"] = target

    if winner_origin:
        _merge_clusters_visual(engine, alert, winner_origin)

    after = {
        "trajectories": alert.get("trajectories"),
        "clusters": alert.get("clusters"),
        "title": alert.get("title"),
        "center": alert.get("center"),
    }
    changed = before != after
    labels = []
    if len(before.get("trajectories") or []) != len(after.get("trajectories") or []):
        labels.append("collapse_trajectories")
    if before.get("clusters") != after.get("clusters"):
        labels.append("rebuild_clusters")
    if before.get("title") != after.get("title"):
        labels.append("retitle")
    if not labels and changed:
        labels.append("refresh_geometry")
    return alert, changed, labels


def dedupe_verified_missile_archive(alert, engine=None):
    """
    For history-fixer commits: drop extra trajectories and align cluster labels.
    Does not move origin_coords on the primary trajectory.
    """
    if not is_history_fixer_committed(alert):
        return alert, False, []

    trajs = alert.get("trajectories") or []
    if not trajs:
        return alert, False, []

    origin = (alert.get("manual_origin") or trajs[0].get("origin") or "").strip()
    if not origin:
        return alert, False, []

    labels = []
    if len(trajs) > 1:
        alert["trajectories"] = [trajs[0]]
        labels.append("dedupe_trajectories")

    clusters = alert.get("clusters") or []
    relabeled = False
    for cluster in clusters:
        if cluster.get("origin") != origin:
            cluster["origin"] = origin
            relabeled = True
    if relabeled:
        labels.append("relabel_clusters")

    display = _display_origin_name(origin)
    expected_title = f"{display} Salvo"
    if alert.get("title") != expected_title:
        alert["title"] = expected_title
        labels.append("retitle")

    if engine is not None:
        before_clusters = copy.deepcopy(alert.get("clusters"))
        _merge_clusters_visual(engine, alert, origin)
        if alert.get("clusters") != before_clusters:
            labels.append("merge_clusters")

    return alert, bool(labels), labels
