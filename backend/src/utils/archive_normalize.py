"""Normalize legacy missile archive payloads to the current single-trajectory schema."""

import copy
import numpy as np

from src.core.origin_ml import collapse_missile_origins, resolve_origin_ml
from src.utils.config import MAX_IRAN_THRESHOLD, MISSILE_INFLATION_FACTOR
from src.utils.trajectory_utils import apply_projected_origin


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

    raw_clusters = engine.cluster(cities)
    processed_clusters = []
    origin_groups = {}

    for rc in raw_clusters:
        raw_org, cl_depth = await engine.get_origin(rc["cities"], allow_strategic=allow_strategic)
        cl_org = raw_org.strip()
        if force_iran:
            cl_org, cl_depth = "Iran", engine.strategic_depths["Iran"]

        processed_clusters.append({
            "origin": cl_org,
            "centroid": rc["centroid"],
            "cities": rc["cities"],
            "hull": engine.get_inflated_hull(
                [c["coords"] for c in rc["cities"]],
                MISSILE_INFLATION_FACTOR,
                cities=rc["cities"],
            ),
        })
        if cl_org not in origin_groups:
            origin_groups[cl_org] = {"cities": [], "depth": cl_depth}
        origin_groups[cl_org]["cities"].extend(rc["cities"])
        origin_groups[cl_org]["depth"] = max(origin_groups[cl_org]["depth"], cl_depth)

    trajectories = []
    for org, group_data in origin_groups.items():
        g_cities = group_data["cities"]
        g_depth = group_data["depth"]
        g_coords = np.array([c["coords"] for c in g_cities])
        g_cnt = np.mean(g_coords, axis=0).tolist()
        traj = {"origin": org, "target_coords": g_cnt, "depth": g_depth}
        apply_projected_origin(engine, traj, g_cities, org, g_depth)
        trajectories.append(traj)

    origin_candidates = None
    if len(origin_groups) == 1:
        org_name = next(iter(origin_groups))
        alert["title"] = f"{_display_origin_name(org_name)} Salvo"
        alert["zoom_level"] = engine.zoom_levels.get(org_name, 6)
    elif len(origin_groups) >= 2:
        candidates = list(origin_groups.keys())
        winner, confidence, scores, resolved_by = await resolve_origin_ml(
            engine, cities, candidates
        )
        if resolved_by == "geometry_fallback" and len(candidates) > 1:
            winner = _pick_winner_from_stored(alert, candidates)
            confidence = scores.get(winner, 0.0) if scores else 0.0
            resolved_by = "archive_stored_winner"
        payload_stub = {
            "clusters": processed_clusters,
            "trajectories": trajectories,
            "all_cities": cities,
        }
        collapse_missile_origins(
            payload_stub, winner, confidence, scores, resolved_by, engine
        )
        processed_clusters = payload_stub["clusters"]
        trajectories = payload_stub["trajectories"]
        alert["title"] = payload_stub["title"]
        alert["zoom_level"] = payload_stub["zoom_level"]
        origin_candidates = payload_stub.get("origin_candidates")
        alert["origin_ml_scores"] = payload_stub.get("origin_ml_scores")
        alert["origin_resolved_by"] = payload_stub.get("origin_resolved_by")
        alert["origin_ml_confidence"] = payload_stub.get("origin_ml_confidence")

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
