import math
import logging
import numpy as np
from scipy.spatial import ConvexHull
from src.utils.text_utils import standardize_name
from src.utils.config import DEFAULT_INFLATION_FACTOR, DRONE_INFLATION_FACTOR, MISSILE_INFLATION_FACTOR

logger = logging.getLogger("IronSightClustering")

AREAS_ADJACENCY = {
    "צפון": ["חיפה"],
    "חיפה": ["צפון", "מרכז", "יהודה ושומרון"],
    "מרכז": ["חיפה", "תל אביב", "ירושלים", "דרום", "יהודה ושומרון"],
    "תל אביב": ["מרכז"],
    "ירושלים": ["מרכז", "יהודה ושומרון", "דרום"],
    "דרום": ["מרכז", "ירושלים"],
    "יהודה ושומרון": ["צפון", "חיפה", "מרכז", "ירושלים"]
}

_R_EARTH = 6371.0  # Radius of earth in kilometers

def haversine_distance(coord1, coord2):
    """Calculate the great circle distance in kilometers between two points on the earth."""
    if not coord1 or not coord2:
        return float('inf')
    lat1, lon1 = np.radians(coord1[0]), np.radians(coord1[1])
    lat2, lon2 = np.radians(coord2[0]), np.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    return _R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def haversine_distance_matrix(coords):
    """Compute NxN pairwise haversine distance matrix from an Nx2 array of [lat,lon] in degrees."""
    rad = np.radians(coords)
    lat = rad[:, 0]
    lon = rad[:, 1]
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2)**2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2)**2
    return _R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def is_subset(cities_a, cities_b):
    """Check if one list of cities is a subset of another, by name."""
    set_a = {c.get('name') for c in cities_a if c.get('name')}
    set_b = {c.get('name') for c in cities_b if c.get('name')}
    if not set_a or not set_b:
        return False
    return set_a.issubset(set_b)

def recalculate_unified_metadata(cities, factor=DRONE_INFLATION_FACTOR):
    """
    Given a list of cities, recalculate a single unified centroid and convex hull.
    This replaces the multiple sub-clusters from merged events.
    """
    if not cities:
        return None, None
        
    coords = np.array([c['coords'] for c in cities])
    centroid = np.mean(coords, axis=0).tolist()
    
    if len(coords) == 1:
        # Create a small tactical diamond for single points
        p = coords[0]
        offset = 0.02  # ~8km tactical buffer
        hull = [
            [p[0] + offset, p[1]],
            [p[0], p[1] + offset],
            [p[0] - offset, p[1]],
            [p[0], p[1] - offset]
        ]
    elif len(coords) == 2:
        # Inflate 2 points away from each other
        cnt = np.array(centroid)
        inflated = cnt + (coords - cnt) * factor
        hull = inflated.tolist()
    else:
        try:
            ch = ConvexHull(coords)
            hull_pts = coords[ch.vertices]
            cnt = np.array(centroid)
            inflated = cnt + (hull_pts - cnt) * factor
            hull = inflated.tolist()
        except:
            hull = coords.tolist()
            
    return centroid, hull

def _compute_adjacency_matrix(items, threshold_km):
    """
    Core vectorized adjacency builder.
    items: List of dicts, each containing:
           - "id": unique identifier
           - "category": threat category
           - "cities": list of city objects
           - "center": [lat, lon] or None
    Returns an NxN boolean adjacency matrix.
    """
    n = len(items)
    if n <= 1:
        return np.eye(n, dtype=bool) if n == 1 else np.empty((0, 0), dtype=bool)

    # 1. Standardize and index cities
    # (v0.9.3: Fix empty string overlaps by filtering standardize_name results)
    item_standardized_cities = []
    all_std_names = set()
    for item in items:
        std_list = []
        for c in item.get("cities", []):
            std = standardize_name(c.get('name'))
            if std:
                std_list.append(std)
                all_std_names.add(std)
        item_standardized_cities.append(std_list)
    
    std_to_idx = {name: i for i, name in enumerate(sorted(all_std_names))}
    num_cities = len(std_to_idx)
    
    # 2. Build presence matrix (N x K)
    presence = np.zeros((n, num_cities), dtype=bool)
    for i, std_list in enumerate(item_standardized_cities):
        for std in std_list:
            presence[i, std_to_idx[std]] = True
    
    city_counts = presence.sum(axis=1) # (N,)
    
    # 3. Vectorized Proximity (Haversine)
    centers = np.array([item.get("center") or [0.0, 0.0] for item in items], dtype=np.float64)
    has_center = np.array([item.get("center") is not None for item in items])
    dist_mat = haversine_distance_matrix(centers)
    
    # 4. Regional Hardening Phase (v0.9.3)
    # Determine majority area for each alert
    alert_areas = []
    for i, std_list in enumerate(item_standardized_cities):
        alert_areas.append(items[i].get("dominant_area", "Unknown"))
    
    # Adjacency calculation (Vectorized pair-wise region checks)
    is_same_area = np.zeros((n, n), dtype=bool)
    is_adjacent_area = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(n):
            a1, a2 = alert_areas[i], alert_areas[j]
            if a1 == a2:
                is_same_area[i, j] = True
            elif a2 in AREAS_ADJACENCY.get(a1, []):
                is_adjacent_area[i, j] = True
    
    # Thresholds: 15km for same/adjacent, 5km for disjoint (Opposites)
    thresholds = np.where(is_same_area | is_adjacent_area, threshold_km, 5.0)
    
    # Gaza Envelope Exception: Relaxed for "דרום"
    is_gaza = np.array([a == "דרום" for a in alert_areas])
    thresholds[is_gaza[:, None] & is_gaza[None, :]] = max(threshold_km, 25.0) 

    # Proximity Rule
    valid_pair = has_center[:, None] & has_center[None, :]
    proximate = valid_pair & (dist_mat <= thresholds)

    # 5. Shared City Rule (Intersection Check)
    # Disjoint regions require 50% subset to merge (Subset Intersection Match)
    intersection = (presence[:, None, :] & presence[None, :, :]).sum(axis=2)
    
    # Intersection must be > 0 always
    has_shared = (intersection > 0)
    
    # For disjoint areas, requires 50% subset of the smaller alert
    min_counts = np.minimum(city_counts[:, None], city_counts[None, :])
    subset_ratio = np.divide(intersection, min_counts, out=np.zeros_like(intersection, dtype=float), where=min_counts>0)
    strong_shared = (subset_ratio >= 0.5) & (intersection > 0)
    
    # Combine Proximity and Shared
    shared_match = np.where(is_same_area | is_gaza[:, None], has_shared, strong_shared)

    # 6. Final Category and Origin Guard
    categories = np.array([item.get("category", "") for item in items])
    origins = np.array([item.get("origin", "Unknown") for item in items])
    cat_match = (categories[:, None] == categories[None, :])
    origin_match = (origins[:, None] == origins[None, :])
    
    return cat_match & origin_match & (proximate | shared_match)

def _get_connected_components(adj_matrix):
    """Utility to extract components from an adjacency matrix."""
    n = adj_matrix.shape[0]
    if n == 0: return []
    
    try:
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import connected_components
        _, labels = connected_components(csr_matrix(adj_matrix))
        components = {}
        for i, label in enumerate(labels):
            components.setdefault(label, []).append(i)
        return list(components.values())
    except ImportError:
        # Fallback to BFS
        visited = np.zeros(n, dtype=bool)
        components = []
        for i in range(n):
            if not visited[i]:
                comp = []
                stack = [i]
                visited[i] = True
                while stack:
                    u = stack.pop()
                    comp.append(u)
                    for v in np.where(adj_matrix[u])[0]:
                        if not visited[v]:
                            visited[v] = True
                            stack.append(v)
                components.append(comp)
        return components


def group_events(active_events, threshold_km=15, include_all=False):
    """
    Groups events into clusters based on proximity and subset rules.
    If include_all=True, it includes ended events (required for history merging).
    Returns a list of clusters (each cluster is a list of event IDs).
    """
    event_items = []
    
    # We need access to area data to determine dominant_area
    # For now, we attempt to resolve the context from the cities
    for eid, ev in active_events.items():
        if include_all or ev.get("end_time") is None:
            data = ev.get("data", {})
            cities = data.get("all_cities", [])
            
            # Simple dominant area detection
            areas = [c.get("area", "Unknown") for c in cities if c.get("area")]
            dominant = max(set(areas), key=areas.count) if areas else "Unknown"
            
            # Extract detected origin for origin-aware merging
            trajectories = data.get("trajectories", [])
            origin = trajectories[0].get("origin", "Unknown") if trajectories else "Unknown"
            
            event_items.append({
                "id": eid,
                "category": ev.get("category", ""),
                "origin": origin,
                "cities": cities,
                "center": data.get("center"),
                "dominant_area": dominant
            })
            
    if not event_items:
        return []

    adj_matrix = _compute_adjacency_matrix(event_items, threshold_km)
    components = _get_connected_components(adj_matrix)
    
    return [[event_items[idx]["id"] for idx in comp] for comp in components]

async def merge_event_group(group_ids, active_events, engine=None):
    """
    Consolidates a group of alert IDs into a single master payload.
    Uses the first lexicographical ID as the stable Master ID.
    """
    if not group_ids:
        return None

    # Single-event groups: return stored data directly (no recalculation).
    # This preserves the original detection context (e.g. newsFlash-gated origins).
    if len(group_ids) == 1:
        eid = group_ids[0]
        ev = active_events[eid]
        data = dict(ev["ev"]["data"] if "ev" in ev else ev["data"])
        data["id"] = eid
        data["merged_ids"] = [eid]
        return data
        
    # Sort IDs for stability
    sorted_ids = sorted(group_ids)
    master_id = sorted_ids[0]
    
    lead_item = active_events[master_id]
    base_data = dict(lead_item["ev"]["data"] if "ev" in lead_item else lead_item["data"])
    base_data["id"] = master_id
    base_data["merged_ids"] = sorted_ids  # Audit traceability (v0.8.8)
    
    category = base_data.get("category")
    merged_all_cities = list(base_data.get("all_cities", []))
    existing_city_names = {c['name'] for c in merged_all_cities if c.get('name')}
    
    # 1. Collect all unique cities from the group
    for other_id in sorted_ids[1:]:
        other_item = active_events[other_id]
        other_data = other_item["ev"]["data"] if "ev" in other_item else other_item["data"]
        for c in other_data.get("all_cities", []):
            if c.get('name') and c['name'] not in existing_city_names:
                merged_all_cities.append(c)
                existing_city_names.add(c['name'])
        
    # 2. Recompute visual structures
    # Starting state: unified lists
    merged_clusters = []
    merged_trajectories = []
    merged_origins = []

    if category in ["missiles", "hostileAircraftIntrusion", "newsFlash"]:
        # Cohesive threats get unified trajectory but can maintain multiple tactical hulls
        coords = np.array([c['coords'] for c in merged_all_cities])
        new_cnt = np.mean(coords, axis=0).tolist()
        base_data["center"] = new_cnt
        
        # Use engine to preserve spatially distinct clusters (e.g. North vs South)
        # Resolve category-specific inflation factor
        if category == "missiles":
            merge_factor = MISSILE_INFLATION_FACTOR
        elif category == "hostileAircraftIntrusion":
            merge_factor = DRONE_INFLATION_FACTOR
        else:
            merge_factor = DEFAULT_INFLATION_FACTOR

        if engine:
            raw_clusters = engine.cluster(merged_all_cities)
            for rc in raw_clusters:
                merged_clusters.append({
                    "origin": category,
                    "centroid": rc['centroid'],
                    "cities": rc['cities'],
                    "hull": engine.get_inflated_hull([c['coords'] for c in rc['cities']], merge_factor)
                })
        else:
            _, new_hull = recalculate_unified_metadata(merged_all_cities, merge_factor)
            merged_clusters = [{
                "origin": category,
                "centroid": new_cnt,
                "cities": merged_all_cities,
                "hull": new_hull
            }]
        
        if category == "missiles" and engine:
            # Smart Multi-Origin Trajectory Grouping (v1.0.2)
            # Strategic origin gate: respect newsFlash context during merge recalculation
            allow_strategic = any(
                ev.get("category") == "newsFlash" and ev.get("end_time") is None
                for ev in active_events.values()
            )
            # Group clusters by their standardized origin to ensure exactly one trajectory per front
            origin_groups = {} # { origin_name: { "cities": [], "depth": float } }
            
            for mc in merged_clusters:
                raw_org, cl_depth = await engine.get_origin(mc['cities'], allow_strategic=allow_strategic)
                cl_org = raw_org.strip()
                mc['origin'] = cl_org 
                
                if cl_org not in origin_groups:
                    origin_groups[cl_org] = {"cities": [], "depth": cl_depth}
                origin_groups[cl_org]["cities"].extend(mc['cities'])
                # Standardize depth: Use the deepest calculated trajectory if multiple exist for same origin
                origin_groups[cl_org]["depth"] = max(origin_groups[cl_org]["depth"], cl_depth)
            
            merged_trajectories = []
            for org, group_data in origin_groups.items():
                g_cities = group_data["cities"]
                g_depth = group_data["depth"]
                # Unified target center for this origin
                g_coords = np.array([c['coords'] for c in g_cities])
                g_cnt = np.mean(g_coords, axis=0).tolist()
                
                # Global origin projection for the entire front
                border_entry = engine.get_projected_origin(g_cities, org, depth=g_depth)
                merged_trajectories.append({
                    "origin": org,
                    "origin_coords": border_entry,
                    "marker_coords": engine.origins.get(org, border_entry),
                    "target_coords": g_cnt,
                    "depth": g_depth
                })
            
            # Multi-origin zoom & centering (v1.0.6)
            if len(origin_groups) > 1:
                base_data["center"] = [31.7, 35.2]
                base_data["zoom_level"] = 6
            elif len(origin_groups) == 1:
                org_name = list(origin_groups.keys())[0]
                base_data["zoom_level"] = engine.zoom_levels.get(org_name, 6)
    else:
        # Multi-cluster threats (Infiltration, Earthquake) accumulate original markers
        merged_clusters = list(base_data.get("clusters", []))
        for other_id in sorted_ids[1:]:
            other_item = active_events[other_id]
            other_data = other_item["ev"]["data"] if "ev" in other_item else other_item["data"]
            merged_clusters.extend(other_data.get("clusters", []))
            # No trajectories for these types
            
    base_data["all_cities"] = merged_all_cities
    base_data["clusters"] = merged_clusters
    base_data["trajectories"] = merged_trajectories
    base_data["highlight_origins"] = merged_origins
    
    if len(sorted_ids) > 1:
        logger.info(f"CLUSTER_MERGED: {len(sorted_ids)} IDs consolidated -> Master ID: {master_id}")
        
    return base_data

async def build_merged_payloads(active_events, engine=None, threshold_km=15):
    """
    Legacy wrapper for websocket broadcast, utilizing refactored grouping logic.
    """
    clusters = group_events(active_events, threshold_km, include_all=False)
    
    merged_payloads = []
    for group_ids in clusters:
        payload = await merge_event_group(group_ids, active_events, engine)
        if payload:
            merged_payloads.append(payload)
            
    return merged_payloads


def get_cluster_groups(active_events, threshold_km=15):
    """
    Lightweight wrapper for cluster-aware timeout synchronization.
    Note: Always filters to active-only events.
    """
    return group_events(active_events, threshold_km, include_all=False)
