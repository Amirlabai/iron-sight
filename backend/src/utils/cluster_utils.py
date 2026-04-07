import math
import logging
import numpy as np
from scipy.spatial import ConvexHull

logger = logging.getLogger("IronSightClustering")

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

def recalculate_unified_metadata(cities):
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
        offset = 0.08  # ~8km tactical buffer
        hull = [
            [p[0] + offset, p[1]],
            [p[0], p[1] + offset],
            [p[0] - offset, p[1]],
            [p[0], p[1] - offset]
        ]
    elif len(coords) == 2:
        # Inflate 2 points away from each other
        cnt = np.array(centroid)
        inflated = cnt + (coords - cnt) * 1.5
        hull = inflated.tolist()
    else:
        try:
            ch = ConvexHull(coords)
            hull_pts = coords[ch.vertices]
            # Inflation Phase (v0.8.7): Expand hull by 50% to encapsulate drone paths
            cnt = np.array(centroid)
            inflated = cnt + (hull_pts - cnt) * 1.5
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

    # 1. Pre-calculate indices for subset detection
    all_city_names = set()
    for item in items:
        for c in item.get("cities", []):
            if c.get('name'): all_city_names.add(c['name'])
    
    city_to_idx = {name: i for i, name in enumerate(sorted(all_city_names))}
    num_cities = len(city_to_idx)
    
    # 2. Build presence matrix (N x K) and presence counts
    presence = np.zeros((n, num_cities), dtype=bool)
    for i, item in enumerate(items):
        for c in item.get("cities", []):
            name = c.get('name')
            if name in city_to_idx:
                presence[i, city_to_idx[name]] = True
    
    city_counts = presence.sum(axis=1) # (N,)
    
    # 3. Vectorized Proximity (Haversine)
    centers = np.array([item.get("center") or [0.0, 0.0] for item in items], dtype=np.float64)
    has_center = np.array([item.get("center") is not None for item in items])
    dist_mat = haversine_distance_matrix(centers)
    valid_pair = has_center[:, None] & has_center[None, :]
    proximate = valid_pair & (dist_mat <= threshold_km)

    # 4. Vectorized Shared City Check
    # Any shared city between two alerts of the same category triggers a merge.
    intersection = (presence[:, None, :] & presence[None, :, :]).sum(axis=2)
    shared_match = (intersection > 0)

    # 5. Combine rules (Category + (Proximity | Shared Cities))
    categories = np.array([item.get("category", "") for item in items])
    cat_match = (categories[:, None] == categories[None, :])
    
    return cat_match & (proximate | shared_match)

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
    for eid, ev in active_events.items():
        if include_all or ev.get("end_time") is None:
            data = ev.get("data", {})
            event_items.append({
                "id": eid,
                "category": ev.get("category", ""),
                "cities": data.get("all_cities", []),
                "center": data.get("center")
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
        
    # Sort IDs for stability
    sorted_ids = sorted(group_ids)
    master_id = sorted_ids[0]
    
    lead_item = active_events[master_id]
    base_data = dict(lead_item["ev"]["data"] if "ev" in lead_item else lead_item["data"])
    base_data["id"] = master_id
    base_data["merged_ids"] = sorted_ids  # Audit traceability (v0.8.8)
    
    category = base_data.get("category")
    
    merged_all_cities = list(base_data.get("all_cities", []))
    merged_clusters = list(base_data.get("clusters", []))
    merged_trajectories = list(base_data.get("trajectories", []))
    merged_origins = list(base_data.get("highlight_origins", []))
    
    existing_city_names = {c['name'] for c in merged_all_cities if c.get('name')}
    
    for other_id in sorted_ids[1:]:
        other_item = active_events[other_id]
        other_data = other_item["ev"]["data"] if "ev" in other_item else other_item["data"]
        
        # Merge unique cities
        for c in other_data.get("all_cities", []):
            if c.get('name') and c['name'] not in existing_city_names:
                merged_all_cities.append(c)
                existing_city_names.add(c['name'])
        
        # Aggregate visual overlays
        merged_trajectories.extend(other_data.get("trajectories", []))
        merged_origins.extend(other_data.get("highlight_origins", []))
        
        if category not in ["missiles", "hostileAircraftIntrusion"]:
            merged_clusters.extend(other_data.get("clusters", []))
            
    # Hardened Unification
    if category in ["missiles", "hostileAircraftIntrusion"]:
        new_cnt, new_hull = recalculate_unified_metadata(merged_all_cities)
        merged_clusters = [{
            "origin": category,
            "centroid": new_cnt,
            "cities": merged_all_cities,
            "hull": new_hull
        }]
        base_data["center"] = new_cnt
        
        if category == "missiles" and len(sorted_ids) > 1 and engine:
            org_name, depth = await engine.get_origin(merged_all_cities)
            border_entry = engine.get_projected_origin(merged_all_cities, org_name, depth=depth)
            merged_trajectories = [{
                "origin": org_name,
                "origin_coords": border_entry,
                "marker_coords": engine.origins.get(org_name, border_entry),
                "target_coords": new_cnt,
                "depth": depth
            }]
            
            # v0.9.0: ML-Based Pruning
            # If the ML match is significantly different from the vector-based origin, 
            # or if the cluster contains cities that are geographically inconsistent, 
            # the engine's _lookup_historical_match will guide the refinement.
            if len(merged_all_cities) > 1:
                ml_origin, ml_depth = engine._lookup_historical_match(merged_all_cities) or (None, None)
                if ml_origin and ml_origin != org_name:
                    logger.warning(f"ML_MISMATCH: Vector says {org_name}, ML says {ml_origin}. Prioritizing ML for verified patterns.")
                    org_name = ml_origin
                    depth = ml_depth
                    border_entry = engine.get_projected_origin(merged_all_cities, org_name, depth=depth)
                    merged_trajectories[0].update({
                        "origin": org_name,
                        "origin_coords": border_entry,
                        "marker_coords": engine.origins.get(org_name, border_entry),
                        "depth": depth
                    })
            
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
