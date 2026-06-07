"""Shared helpers for missile trajectory payloads."""


def set_trajectory_entry(traj, coords):
    """Set origin pin and line start to the same border-entry coordinates."""
    traj["origin_coords"] = coords
    traj["marker_coords"] = coords


def apply_projected_origin(engine, traj, cities, origin_name, depth):
    """Project display pin (tactical country) and store optional calc entry."""
    display, calc_entry = engine.project_origin_display(cities, origin_name, depth=depth)
    set_trajectory_entry(traj, display)
    traj.pop("calc_entry_coords", None)
    if calc_entry is not None:
        traj["calc_entry_coords"] = calc_entry
    return display


def _origin_depth(engine, origin):
    if origin in engine.strategic_depths:
        return engine.strategic_depths[origin]
    if origin == "Iran":
        return engine.strategic_depths.get("Iran", 13.0)
    return 0.5


def entry_by_origin(engine, cities, candidates):
    """Project calc-border entry for each origin candidate."""
    result = {}
    for origin in candidates:
        if not origin:
            continue
        depth = _origin_depth(engine, origin)
        entry = engine.project_calc_entry(cities, origin, depth=depth)
        if entry is not None:
            result[origin] = [float(entry[0]), float(entry[1])]
    return result


def project_entry_for_origin(engine, cities, origin_name):
    """Single-origin border entry projection."""
    entries = entry_by_origin(engine, cities, [origin_name])
    return entries.get(origin_name)


def _mean_city_coords(cities):
    coords = [
        c["coords"] for c in (cities or [])
        if c.get("coords") and len(c["coords"]) >= 2
    ]
    if not coords:
        return None
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return [float(lat), float(lon)]


def sync_missile_trajectory_on_verify(traj, origin_name, entry_coords, cities, engine):
    """Rewrite trajectory geometry on history-fixer verify commit."""
    traj["origin"] = origin_name
    set_trajectory_entry(traj, entry_coords)
    traj["depth"] = _origin_depth(engine, origin_name)
    target = _mean_city_coords(cities)
    if target:
        traj["target_coords"] = target
    zoom = engine.zoom_levels.get(
        origin_name,
        engine.zoom_levels.get("Iran", 6) if "Iran" in origin_name else 8,
    )
    traj["zoom"] = zoom
    return traj
