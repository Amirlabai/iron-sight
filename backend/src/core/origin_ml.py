"""Verified-history scoring when two or more geometric origin candidates exist."""
import logging
import numpy as np

logger = logging.getLogger("IronSightBackend")

ML_SCORE_FLOOR = 0.15
REGIONAL_ORIGINS = ("Lebanon", "Gaza")
STRATEGIC_ORIGINS = ("Iran", "Yemen", "North Iran")


def normalize_origin_label(origin):
    if not origin:
        return "Unknown"
    o = origin.strip()
    if o in ("Iran", "North Iran"):
        return "Iran"
    return o


def _record_origin_label(item):
    trajectories = item.get("trajectories") or []
    if not trajectories:
        return None
    return normalize_origin_label(trajectories[0].get("origin"))


def score_cities_against_record(cities, item):
    """Return similarity score in [0, 1] between current cities and one verified record."""
    trajectories = item.get("trajectories")
    if not trajectories:
        return 0.0

    current_names = {c.get("name") for c in cities if c.get("name")}
    if not current_names:
        return 0.0

    hist_names = {c.get("name") for c in item.get("all_cities", []) if c.get("name")}
    if current_names == hist_names:
        return 1.0

    current_centroid = np.mean([c["coords"] for c in cities], axis=0)
    hist_centroid = np.array(item.get("center") or [0, 0])
    dist_km = np.linalg.norm(current_centroid - hist_centroid) * 111.0

    intersection = current_names.intersection(hist_names)
    union = current_names.union(hist_names)
    jaccard = len(intersection) / len(union) if union else 0.0

    if dist_km >= 5.0 or jaccard <= 0.8:
        return 0.0

    proximity = float(np.exp(-dist_km / 5.0))
    return jaccard * proximity


def score_origin_candidate(cities, origin_label, verified_history):
    """Max score over verified records labeled with this origin."""
    target = normalize_origin_label(origin_label)
    best = 0.0
    for item in verified_history or []:
        if _record_origin_label(item) != target:
            continue
        best = max(best, score_cities_against_record(cities, item))
    return best


def geometric_tiebreak(candidates):
    """Prefer regional origins over strategic when ML has no signal."""
    normalized = [normalize_origin_label(c) for c in candidates]
    for pref in ("Lebanon", "Gaza", "Iran", "Yemen"):
        if pref in normalized:
            idx = normalized.index(pref)
            return candidates[idx].strip() if candidates[idx] else pref
    return candidates[0].strip() if candidates else "Lebanon"


async def resolve_origin_ml(engine, cities, candidates):
    """
    Score each candidate against verified history. Only meaningful when len(candidates) >= 2.
    Returns (winner, confidence, scores_dict, resolved_by).
    """
    if len(candidates) < 2:
        raise ValueError("resolve_origin_ml requires at least two candidates")

    await engine._sync_verified_history()
    verified = engine.verified_history or []

    scores = {}
    for cand in candidates:
        label = normalize_origin_label(cand)
        scores[label] = max(scores.get(label, 0.0), score_origin_candidate(cities, label, verified))

    total = sum(scores.values())
    if total <= 0 or max(scores.values()) < ML_SCORE_FLOOR:
        winner = geometric_tiebreak(candidates)
        logger.info(f"ML_ORIGIN_LOW_CONFIDENCE: fallback -> {winner} candidates={candidates}")
        return winner, 0.0, scores, "geometry_fallback"

    winner = max(scores, key=scores.get)
    confidence = scores[winner] / total if total > 0 else 0.0
    logger.info(f"ML_ORIGIN_RESOLVED: {winner} confidence={confidence:.2f} scores={scores}")
    return winner, confidence, scores, "ml"


def collapse_missile_origins(payload, winner, confidence, scores, resolved_by, engine):
    """Rewrite missiles payload to a single origin / trajectory after ML disambiguation."""
    all_cities = payload.get("all_cities") or []
    if not all_cities:
        return payload

    display_origin = "Iran" if winner == "North Iran" else winner
    depth = engine.strategic_depths.get(winner, engine.strategic_depths.get("Iran", 16.0) if winner == "Iran" else 0.5)

    g_coords = np.array([c["coords"] for c in all_cities])
    g_cnt = np.mean(g_coords, axis=0).tolist()
    border_entry = engine.get_projected_origin(all_cities, winner, depth=depth)

    for cluster in payload.get("clusters", []):
        cluster["origin"] = winner

    payload["trajectories"] = [{
        "origin": winner,
        "origin_coords": border_entry,
        "marker_coords": engine.origins.get(winner, border_entry),
        "target_coords": g_cnt,
        "depth": depth,
    }]
    payload["title"] = f"{display_origin} Salvo"
    payload["zoom_level"] = engine.zoom_levels.get(winner, 6)
    payload["origin_candidates"] = list(scores.keys())
    payload["origin_ml_scores"] = scores
    payload["origin_resolved_by"] = resolved_by
    payload["origin_ml_confidence"] = confidence
    return payload
