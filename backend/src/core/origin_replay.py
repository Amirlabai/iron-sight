"""Step-by-step origin pipeline trace for dev replay tooling."""

import numpy as np
from src.utils.config import MAX_IRAN_THRESHOLD, MISSILE_INFLATION_FACTOR
from src.core.origin_ml import resolve_origin_ml, collapse_missile_origins
from src.utils.trajectory_utils import set_trajectory_entry

CLUSTER_COLORS = ["#ff6b6b", "#4dabf7", "#51cf66", "#fcc419", "#cc5de8"]
TERRITORY_COLORS = {
    "Gaza": "#ff3b30",
    "Lebanon": "#ff9500",
    "Iran": "#af52de",
    "North Iran": "#af52de",
    "Yemen": "#ffcc00",
}


def _city_markers(cities, color="#ff4d4d"):
    return [
        {
            "lat": c["coords"][0],
            "lon": c["coords"][1],
            "label": c.get("name", ""),
            "color": color,
        }
        for c in cities
        if c.get("coords")
    ]


def _hull_polygon(hull, color, fill_opacity=0.15):
    if not hull or len(hull) < 2:
        return None
    return {"rings": [hull], "color": color, "fillOpacity": fill_opacity}


def _vector_arrow(centroid, vector, scale=1.0, color="#0066ff", dashed=False):
    if not vector or not centroid:
        return None
    v_lat, v_lon = vector
    mag = (v_lat ** 2 + v_lon ** 2) ** 0.5
    if mag == 0:
        return None
    v_lat, v_lon = v_lat / mag, v_lon / mag
    end = [centroid[0] + v_lat * scale, centroid[1] + v_lon * scale]
    return {
        "points": [centroid, end],
        "color": color,
        "dashed": dashed,
    }


def _territory_polygons(engine, names):
    polys = []
    for name in names:
        boundary = engine.calc_boundaries.get(name)
        if not boundary:
            continue
        if engine._boundary_is_multi_ring(boundary):
            rings = boundary
        else:
            rings = [boundary]
        polys.append({
            "rings": rings,
            "color": TERRITORY_COLORS.get(name, "#888888"),
            "fillOpacity": 0.08,
            "label": name,
        })
    return polys


def _step(step_id, title, summary, visuals=None, decision=None):
    return {
        "id": step_id,
        "title": title,
        "summary": summary,
        "decision": decision or {},
        "visuals": visuals or {},
    }


def _is_verified_manual(stored):
    return bool(stored and (stored.get("verified") or stored.get("manual_origin")))


def _stored_entry_for_origin(stored, origin):
    for traj in stored.get("trajectories") or []:
        if traj.get("origin") != origin:
            continue
        coords = traj.get("origin_coords") or traj.get("marker_coords")
        if coords and len(coords) >= 2:
            return [float(coords[0]), float(coords[1])]
    return None


def _trajectory_line_visuals(trajectories, dashed=True):
    visuals = {"markers": [], "polylines": []}
    for t in trajectories:
        org = t["origin"]
        entry = t["origin_coords"]
        target = t["target_coords"]
        color = TERRITORY_COLORS.get(org, "#ffffff")
        visuals["markers"].extend([
            {"lat": entry[0], "lon": entry[1], "label": f"{org} entry", "color": color},
            {"lat": target[0], "lon": target[1], "label": "target", "color": "#ff4d4d"},
        ])
        visuals["polylines"].append({
            "points": [entry, target],
            "color": color,
            "dashed": dashed,
        })
    return visuals


def _trajectory_final_visuals(trajectories, cities):
    visuals = _trajectory_line_visuals(trajectories, dashed=False)
    visuals["markers"].extend(_city_markers(cities, "#ff4d4d"))
    return visuals


def _apply_verified_overlays(steps, trajectories, cities, stored, cnt):
    """Replace PCA-computed entry points with operator-verified coords on display steps."""
    for traj in trajectories:
        org = traj.get("origin")
        stored_entry = _stored_entry_for_origin(stored, org)
        if stored_entry:
            set_trajectory_entry(traj, stored_entry)

    for step in steps:
        if not step["id"].startswith("origin_decided_"):
            continue
        org = step.get("decision", {}).get("origin")
        stored_entry = _stored_entry_for_origin(stored, org)
        if not stored_entry:
            continue
        step["summary"] = (
            f"Origin: {org} (verified manual — operator pin is border entry)."
        )
        step["decision"]["method"] = "verified_manual"
        markers = [
            m for m in step["visuals"].get("markers", [])
            if not (m.get("label") or "").endswith("calc entry")
        ]
        markers.append({
            "lat": stored_entry[0],
            "lon": stored_entry[1],
            "label": f"{org} verified entry",
            "color": TERRITORY_COLORS.get(org, "#ffffff"),
        })
        step["visuals"]["markers"] = markers
        step["visuals"]["polylines"] = [{
            "points": [cnt, stored_entry],
            "color": TERRITORY_COLORS.get(org, "#ffffff"),
            "dashed": True,
        }]

    line_visuals = _trajectory_line_visuals(trajectories, dashed=True)
    final_visuals = _trajectory_final_visuals(trajectories, cities)
    for step in steps:
        if step["id"] == "trajectories":
            step["title"] = "Border projection (verified manual)"
            step["summary"] = (
                f"{len(trajectories)} trajectory line(s) using operator-verified border entry."
            )
            step["visuals"] = line_visuals
            step["decision"] = {"method": "verified_manual", "trajectory_count": len(trajectories)}
        elif step["id"] == "final":
            step["visuals"] = final_visuals
            step["decision"]["method"] = "verified_manual"


async def build_origin_replay(
    engine,
    cities,
    *,
    allow_strategic=True,
    force_iran=False,
    stored=None,
):
    """Run the missile origin pipeline and return ordered replay steps with map visuals."""
    steps = []
    if not cities:
        return {"steps": [], "final": None}

    cnt = np.mean([c["coords"] for c in cities], axis=0).tolist()
    unified_hull = engine.get_inflated_hull(
        [c["coords"] for c in cities], MISSILE_INFLATION_FACTOR, cities=cities
    )

    steps.append(_step(
        "map_cities",
        "Map cities",
        f"{len(cities)} cities mapped to coordinates.",
        {
            "markers": _city_markers(cities),
            "polygons": [_hull_polygon(unified_hull, "#ff4d4d")] if unified_hull else [],
        },
        {"city_count": len(cities), "center": cnt},
    ))

    total_unique = len({c["name"] for c in cities})
    force_iran_active = force_iran or (total_unique > MAX_IRAN_THRESHOLD and allow_strategic)
    steps.append(_step(
        "strategic_gate",
        "Strategic gate",
        (
            f"allow_strategic={allow_strategic}. "
            f"force_iran={force_iran_active} ({total_unique} unique cities, threshold={MAX_IRAN_THRESHOLD})."
        ),
        {
            "markers": _city_markers(cities, "#888888"),
            "annotations": [{"lat": cnt[0], "lon": cnt[1], "text": f"strategic={'ON' if allow_strategic else 'OFF'}"}],
        },
        {
            "allow_strategic": allow_strategic,
            "force_iran": force_iran_active,
            "unique_cities": total_unique,
        },
    ))

    raw_clusters = engine.cluster(cities)
    cluster_visuals = {"markers": [], "polygons": [], "annotations": []}
    for i, rc in enumerate(raw_clusters):
        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        cluster_visuals["markers"].extend(_city_markers(rc["cities"], color))
        hull = engine.get_inflated_hull(
            [c["coords"] for c in rc["cities"]], MISSILE_INFLATION_FACTOR, cities=rc["cities"]
        )
        poly = _hull_polygon(hull, color, 0.2)
        if poly:
            cluster_visuals["polygons"].append(poly)
        c = rc["centroid"]
        cluster_visuals["annotations"].append({
            "lat": c[0], "lon": c[1], "text": f"Cluster {i} ({len(rc['cities'])} cities)",
        })

    steps.append(_step(
        "cluster",
        "Spatial cluster (25 km)",
        f"{len(raw_clusters)} cluster(s) from connected-components grouping.",
        cluster_visuals,
        {"cluster_count": len(raw_clusters)},
    ))

    processed_clusters = []
    origin_groups = {}
    cluster_traces = []

    for i, rc in enumerate(raw_clusters):
        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        trace = await engine.trace_cluster_origin(rc["cities"], allow_strategic=allow_strategic)
        cluster_traces.append(trace)

        base_markers = _city_markers(rc["cities"], color)
        centroid = trace["centroid"]

        hist_summary = (
            f"Historical match → {trace['origin']} (depth {trace['depth']})"
            if trace["method"] == "historical"
            else "No verified historical match for this city set."
        )
        steps.append(_step(
            f"hist_match_{i}",
            f"Cluster {i} — historical match",
            hist_summary,
            {
                "markers": base_markers,
                "annotations": [{"lat": centroid[0], "lon": centroid[1], "text": trace["method"]}],
            },
            {
                "matched": trace["method"] == "historical",
                "origin": trace["origin"] if trace["method"] == "historical" else None,
            },
        ))

        if trace["method"] != "historical" and trace.get("vector"):
            norm = engine._normalize_regression_vector(trace["vector"])
            v_lat, v_lon, _ = engine._orient_vector_away_from(
                centroid, norm[0], norm[1], [31.7, 35.2], len(rc["cities"])
            )
            raw_arrow = _vector_arrow(centroid, trace["vector"], scale=0.8, color="#999999", dashed=True)
            oriented_arrow = _vector_arrow(centroid, [v_lat, v_lon], scale=1.2, color="#0066ff")
            polylines = [p for p in [raw_arrow, oriented_arrow] if p]
            flip_note = "flipped away from Israel" if trace["vector_flipped"] else "no flip needed"
            steps.append(_step(
                f"vector_{i}",
                f"Cluster {i} — regression vector",
                f"PCA eigenvector oriented: {flip_note}.",
                {"markers": base_markers, "polylines": polylines},
                {"method": "vector_orient", "flipped": trace["vector_flipped"]},
            ))

            regional_polys = _territory_polygons(engine, ["Gaza", "Lebanon"])
            regional_markers = list(base_markers)
            if trace.get("regional_proj"):
                regional_markers.append({
                    "lat": trace["regional_proj"][0],
                    "lon": trace["regional_proj"][1],
                    "label": "proj@0.5",
                    "color": "#ff9500",
                })
            hit = trace.get("regional_hit") or "none"
            steps.append(_step(
                f"regional_proj_{i}",
                f"Cluster {i} — Gaza/Lebanon @ 0.5",
                f"Projection at depth 0.5 → territory hit: {hit}.",
                {
                    "markers": regional_markers,
                    "polygons": regional_polys,
                    "polylines": [_vector_arrow(centroid, [v_lat, v_lon], scale=0.5, color="#ff9500")] if trace.get("vector") else [],
                },
                {"depth": 0.5, "hit": trace.get("regional_hit"), "proj": trace.get("regional_proj")},
            ))

            if trace.get("strategic_skipped"):
                steps.append(_step(
                    f"strategic_proj_{i}",
                    f"Cluster {i} — Iran/Yemen @ 7",
                    "Skipped — allow_strategic is false (no newsFlash context).",
                    {"markers": base_markers},
                    {"skipped": True},
                ))
            elif trace.get("vector"):
                strategic_polys = _territory_polygons(engine, ["North Iran", "Iran", "Yemen"])
                strategic_markers = list(base_markers)
                if trace.get("strategic_proj"):
                    strategic_markers.append({
                        "lat": trace["strategic_proj"][0],
                        "lon": trace["strategic_proj"][1],
                        "label": "proj@7",
                        "color": "#af52de",
                    })
                strat_hit = trace.get("strategic_hit") or "none"
                steps.append(_step(
                    f"strategic_proj_{i}",
                    f"Cluster {i} — Iran/Yemen @ 7",
                    f"Strategic projection at depth 7 → territory hit: {strat_hit}.",
                    {
                        "markers": strategic_markers,
                        "polygons": strategic_polys,
                        "polylines": [_vector_arrow(centroid, [v_lat, v_lon], scale=7.0, color="#af52de", dashed=True)],
                    },
                    {"depth": 7, "hit": trace.get("strategic_hit"), "proj": trace.get("strategic_proj")},
                ))

            if trace["method"] == "fallback" and trace.get("fallback"):
                fb = trace["fallback"]
                steps.append(_step(
                    f"fallback_{i}",
                    f"Cluster {i} — fallback heuristic",
                    (
                        f"No polygon hit. Gaza dist={fb['dist_gaza']:.3f}, "
                        f"Lebanon dist={fb['dist_lebanon']:.3f} → {trace['origin']}."
                    ),
                    {
                        "markers": base_markers + [
                            {"lat": engine.origins["Gaza"][0], "lon": engine.origins["Gaza"][1], "label": "Gaza", "color": TERRITORY_COLORS["Gaza"]},
                            {"lat": engine.origins["Lebanon"][0], "lon": engine.origins["Lebanon"][1], "label": "Lebanon", "color": TERRITORY_COLORS["Lebanon"]},
                        ],
                    },
                    {"dist_gaza": fb["dist_gaza"], "dist_lebanon": fb["dist_lebanon"], "origin": trace["origin"]},
                ))
        elif trace["method"] == "fallback" and trace.get("fallback"):
            fb = trace["fallback"]
            steps.append(_step(
                f"fallback_{i}",
                f"Cluster {i} — fallback heuristic",
                (
                    f"No vector available. Gaza dist={fb['dist_gaza']:.3f}, "
                    f"Lebanon dist={fb['dist_lebanon']:.3f} → {trace['origin']}."
                ),
                {
                    "markers": base_markers + [
                        {"lat": engine.origins["Gaza"][0], "lon": engine.origins["Gaza"][1], "label": "Gaza", "color": TERRITORY_COLORS["Gaza"]},
                        {"lat": engine.origins["Lebanon"][0], "lon": engine.origins["Lebanon"][1], "label": "Lebanon", "color": TERRITORY_COLORS["Lebanon"]},
                    ],
                },
                {"dist_gaza": fb["dist_gaza"], "dist_lebanon": fb["dist_lebanon"], "origin": trace["origin"]},
            ))

        cl_org = trace["origin"]
        cl_depth = trace["depth"]
        if force_iran_active:
            cl_org = "Iran"
            cl_depth = engine.strategic_depths["Iran"]

        decided_markers = list(base_markers)
        preview_entry = engine.get_projected_origin(rc["cities"], cl_org, depth=cl_depth)
        decided_markers.append({
            "lat": preview_entry[0],
            "lon": preview_entry[1],
            "label": f"{cl_org} calc entry",
            "color": TERRITORY_COLORS.get(cl_org, "#ffffff"),
        })
        if len(rc["cities"]) >= 2 and engine._oriented_regression_vector(rc["cities"], centroid):
            decided_polylines = [{
                "points": [centroid, preview_entry],
                "color": TERRITORY_COLORS.get(cl_org, "#ffffff"),
                "dashed": True,
            }]
        else:
            decided_polylines = []

        steps.append(_step(
            f"origin_decided_{i}",
            f"Cluster {i} — origin decided",
            f"Origin: {cl_org} (depth {cl_depth}, method={trace['method']}).",
            {
                "markers": decided_markers,
                "polylines": decided_polylines,
            },
            {"origin": cl_org, "depth": cl_depth, "method": trace["method"]},
        ))

        processed_clusters.append({
            "origin": cl_org,
            "centroid": rc["centroid"],
            "cities": rc["cities"],
            "hull": engine.get_inflated_hull(
                [c["coords"] for c in rc["cities"]], MISSILE_INFLATION_FACTOR, cities=rc["cities"]
            ),
        })
        if cl_org not in origin_groups:
            origin_groups[cl_org] = {"cities": [], "depth": cl_depth}
        origin_groups[cl_org]["cities"].extend(rc["cities"])
        origin_groups[cl_org]["depth"] = max(origin_groups[cl_org]["depth"], cl_depth)

    group_visuals = {"markers": [], "polygons": [], "annotations": []}
    for org, group_data in origin_groups.items():
        g_color = TERRITORY_COLORS.get(org, "#ffffff")
        group_visuals["markers"].extend(_city_markers(group_data["cities"], g_color))
        group_visuals["annotations"].append({
            "lat": engine.origins.get(org, [0, 0])[0],
            "lon": engine.origins.get(org, [0, 0])[1],
            "text": f"{org} ({len(group_data['cities'])} cities)",
        })

    steps.append(_step(
        "origin_groups",
        "Group by origin",
        f"{len(origin_groups)} origin group(s): {', '.join(origin_groups.keys())}.",
        group_visuals,
        {"groups": {k: len(v["cities"]) for k, v in origin_groups.items()}},
    ))

    trajectories = []
    traj_visuals = {"markers": [], "polylines": []}
    for org, group_data in origin_groups.items():
        g_cities = group_data["cities"]
        g_depth = group_data["depth"]
        g_coords = np.array([c["coords"] for c in g_cities])
        g_cnt = np.mean(g_coords, axis=0).tolist()
        border_entry = engine.get_projected_origin(g_cities, org, depth=g_depth)
        centroid = engine._cluster_centroid(g_cities)
        oriented = engine._oriented_regression_vector(g_cities, centroid)
        march_depth = None
        if oriented:
            _, march_depth = engine._ray_march_calc_entry(
                centroid, oriented[0], oriented[1], org,
                engine._projection_max_depth(org, g_depth),
            )
        traj = {
            "origin": org,
            "target_coords": g_cnt,
            "depth": g_depth,
            "calc_march_depth": march_depth,
        }
        set_trajectory_entry(traj, border_entry)
        trajectories.append(traj)
        traj_visuals["markers"].extend([
            {"lat": border_entry[0], "lon": border_entry[1], "label": f"{org} entry", "color": TERRITORY_COLORS.get(org, "#fff")},
            {"lat": g_cnt[0], "lon": g_cnt[1], "label": "target", "color": "#ff4d4d"},
        ])
        traj_visuals["polylines"].append({
            "points": [border_entry, g_cnt],
            "color": TERRITORY_COLORS.get(org, "#ffffff"),
            "dashed": True,
        })

    steps.append(_step(
        "trajectories",
        "Border projection (calc ray-march)",
        f"{len(trajectories)} trajectory line(s): calc-border entry along regression ray (no center-pin snap).",
        traj_visuals,
        {
            "trajectory_count": len(trajectories),
            "entries": [
                {"origin": t["origin"], "calc_march_depth": t.get("calc_march_depth")}
                for t in trajectories
            ],
        },
    ))

    title = "Missile Salvo"
    zoom_level = 6
    origin_candidates = None
    origin_ml_scores = None
    origin_resolved_by = None
    origin_ml_confidence = None

    if len(origin_groups) == 1:
        org_name = list(origin_groups.keys())[0]
        display_origin = "Iran" if org_name == "North Iran" else org_name
        title = f"{display_origin} Salvo"
        zoom_level = engine.zoom_levels.get(org_name, 6)
    elif len(origin_groups) >= 2:
        candidates = list(origin_groups.keys())
        winner, confidence, scores, resolved_by = await resolve_origin_ml(
            engine, cities, candidates
        )
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
        title = payload_stub["title"]
        zoom_level = payload_stub["zoom_level"]
        origin_candidates = payload_stub.get("origin_candidates")
        origin_ml_scores = payload_stub.get("origin_ml_scores")
        origin_resolved_by = payload_stub.get("origin_resolved_by")
        origin_ml_confidence = payload_stub.get("origin_ml_confidence")

        score_text = ", ".join(f"{k}={v:.3f}" for k, v in (scores or {}).items())
        ml_markers = _city_markers(cities)
        steps.append(_step(
            "ml_disambiguation",
            "ML tie-break",
            f"Winner: {winner} (confidence {confidence:.2f}, resolved_by={resolved_by}). Scores: {score_text}.",
            {"markers": ml_markers},
            {
                "candidates": candidates,
                "scores": scores,
                "winner": winner,
                "confidence": confidence,
                "resolved_by": resolved_by,
            },
        ))

    final_origin = trajectories[0]["origin"] if len(trajectories) == 1 else None
    if len(origin_groups) >= 2 and origin_ml_scores:
        final_origin = max(origin_ml_scores, key=origin_ml_scores.get)
    elif not final_origin and trajectories:
        final_origin = trajectories[0]["origin"]

    final_visuals = {"markers": [], "polylines": []}
    for t in trajectories:
        org = t["origin"]
        final_visuals["markers"].extend([
            {"lat": t["origin_coords"][0], "lon": t["origin_coords"][1], "label": org, "color": TERRITORY_COLORS.get(org, "#fff")},
            {"lat": t["target_coords"][0], "lon": t["target_coords"][1], "label": "target", "color": "#ff4d4d"},
        ])
        final_visuals["polylines"].append({
            "points": [t["origin_coords"], t["target_coords"]],
            "color": TERRITORY_COLORS.get(org, "#ffffff"),
            "dashed": False,
        })
    final_visuals["markers"].extend(_city_markers(cities, "#ff4d4d"))

    steps.append(_step(
        "final",
        "Final result",
        f"Title: {title}. Primary origin: {final_origin}.",
        final_visuals,
        {
            "title": title,
            "origin": final_origin,
            "zoom_level": zoom_level,
            "origin_candidates": origin_candidates,
            "origin_ml_scores": origin_ml_scores,
            "origin_resolved_by": origin_resolved_by,
            "origin_ml_confidence": origin_ml_confidence,
        },
    ))

    final = {
        "title": title,
        "origin": final_origin,
        "zoom_level": zoom_level,
        "clusters": processed_clusters,
        "trajectories": trajectories,
        "all_cities": cities,
        "center": cnt,
        "origin_candidates": origin_candidates,
        "origin_ml_scores": origin_ml_scores,
        "origin_resolved_by": origin_resolved_by,
        "origin_ml_confidence": origin_ml_confidence,
    }

    if _is_verified_manual(stored):
        _apply_verified_overlays(steps, trajectories, cities, stored, cnt)
        final["trajectories"] = trajectories
        final["verified_manual"] = True

    return {"steps": steps, "final": final}
