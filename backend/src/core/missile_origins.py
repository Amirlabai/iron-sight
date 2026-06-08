"""Shared missile origin grouping: spatial clusters → trajectories → optional ML collapse."""

import numpy as np

from src.core.origin_ml import resolve_origin_ml, collapse_missile_origins
from src.utils.trajectory_utils import apply_projected_origin


def display_origin_name(org_name):
    return "Iran" if org_name == "North Iran" else org_name


def apply_large_salvo_iran_policy(cl_org, cl_depth, force_iran, engine):
    """Nationwide salvo heuristic: assume Iran above city-count threshold.

    Skipped when geometry already resolved to Yemen (strategic projection).
    """
    if not force_iran:
        return cl_org, cl_depth
    if (cl_org or "").strip() == "Yemen":
        return cl_org, cl_depth
    return "Iran", engine.strategic_depths["Iran"]


async def build_missile_origins(
    engine,
    spatial_clusters,
    all_cities,
    *,
    allow_strategic,
    force_iran=False,
    hull_for_cities,
    ml_winner_resolver=None,
):
    """
    Build processed clusters, trajectories, title, and zoom from engine.cluster output.
    hull_for_cities: callable(cities) -> hull polygon
    ml_winner_resolver: optional (winner, confidence, scores, resolved_by, candidates) -> (winner, confidence, resolved_by)
    """
    processed_clusters = []
    origin_groups = {}

    for rc in spatial_clusters:
        raw_org, cl_depth = await engine.get_origin(rc["cities"], allow_strategic=allow_strategic)
        cl_org = raw_org.strip()
        cl_org, cl_depth = apply_large_salvo_iran_policy(
            cl_org, cl_depth, force_iran, engine
        )

        processed_clusters.append({
            "origin": cl_org,
            "centroid": rc["centroid"],
            "cities": rc["cities"],
            "hull": hull_for_cities(rc["cities"]),
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

    result = {
        "clusters": processed_clusters,
        "trajectories": trajectories,
        "title": "Missile Salvo",
        "zoom_level": 6,
        "origin_candidates": None,
        "origin_ml_scores": None,
        "origin_resolved_by": None,
        "origin_ml_confidence": None,
    }

    if len(origin_groups) == 1:
        org_name = next(iter(origin_groups))
        result["title"] = f"{display_origin_name(org_name)} Salvo"
        result["zoom_level"] = engine.zoom_levels.get(org_name, 6)
    elif len(origin_groups) >= 2:
        candidates = list(origin_groups.keys())
        winner, confidence, scores, resolved_by = await resolve_origin_ml(
            engine, all_cities, candidates
        )
        if ml_winner_resolver:
            winner, confidence, resolved_by = ml_winner_resolver(
                winner, confidence, scores, resolved_by, candidates
            )
        payload_stub = {
            "clusters": processed_clusters,
            "trajectories": trajectories,
            "all_cities": all_cities,
        }
        collapse_missile_origins(
            payload_stub, winner, confidence, scores, resolved_by, engine
        )
        result["clusters"] = payload_stub["clusters"]
        result["trajectories"] = payload_stub["trajectories"]
        result["title"] = payload_stub["title"]
        result["zoom_level"] = payload_stub["zoom_level"]
        result["origin_candidates"] = payload_stub.get("origin_candidates")
        result["origin_ml_scores"] = payload_stub.get("origin_ml_scores")
        result["origin_resolved_by"] = payload_stub.get("origin_resolved_by")
        result["origin_ml_confidence"] = payload_stub.get("origin_ml_confidence")

    return result
