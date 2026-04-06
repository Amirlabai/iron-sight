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

def _build_adjacency_components(active_items, threshold_km):
    """
    Fully vectorized adjacency builder. Returns connected components as lists of indices.
    Uses Haversine matrix for proximity and binary matrix operations for subset detection.
    """
    n = len(active_items)
    if n <= 1:
        return [[0]] if n == 1 else []

    # 1. Pre-calculate indices for subset detection
    all_city_names = set()
    for item in active_items:
        for c in item["ev"]["data"].get("all_cities", []):
            if c.get('name'): all_city_names.add(c['name'])
    
    city_to_idx = {name: i for i, name in enumerate(sorted(all_city_names))}
    num_cities = len(city_to_idx)
    
    # 2. Build presence matrix (N x K) and presence counts
    presence = np.zeros((n, num_cities), dtype=bool)
    for i, item in enumerate(active_items):
        for c in item["ev"]["data"].get("all_cities", []):
            name = c.get('name')
            if name in city_to_idx:
                presence[i, city_to_idx[name]] = True
    
    city_counts = presence.sum(axis=1) # (N,)
    
    # 3. Vectorized Proximity (Haversine)
    centers = np.array([item["ev"]["data"].get("center") or [0.0, 0.0] for item in active_items], dtype=np.float64)
    has_center = np.array([item["ev"]["data"].get("center") is not None for item in active_items])
    dist_mat = haversine_distance_matrix(centers)
    valid_pair = has_center[:, None] & has_center[None, :]
    proximate = valid_pair & (dist_mat <= threshold_km)

    # 4. Vectorized Subset Check (Linear Algebra: I = M @ M.T)
    # i is subset of j if (M_i . M_j) == sum(M_i)
    # Using bitwise_and on boolean arrays for better memory if n is small
    # For O(N^2) but with boolean acceleration:
    intersection = (presence[:, None, :] & presence[None, :, :]).sum(axis=2)
    is_subset = (intersection == city_counts[:, None]) & (city_counts[:, None] > 0)
    is_superset = (intersection == city_counts[None, :]) & (city_counts[None, :] > 0)
    subset_match = is_subset | is_superset

    # 5. Combine rules (Category + (Proximity | Subset))
    categories = np.array([item["ev"].get("category", "") for item in active_items])
    cat_match = (categories[:, None] == categories[None, :])
    
    adj_matrix = cat_match & (proximate | subset_match)

    # 6. Extract components using scipy.sparse (if available) or BFS
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


def build_merged_payloads(active_events, engine=None, threshold_km=15):
    """
    Implements intelligent payload broadcast parsing.
    1. Subset Rule: If Event A's cities are a subset of Event B, merge A into B.
    2. Proximity Rule: If Event A and B share the same category and their centroids are within the tactical threshold, merge them.
    3. Transitive Rules: If A matches B and B matches C, all three form a single cluster.
    
    Returns a unified multi_alert payload list.
    """
    # Filter to active only
    active_items = []
    for eid, ev in active_events.items():
        if ev.get("end_time") is None:
            active_items.append({"eid": eid, "ev": ev})
            
    if not active_items:
        return []

    # Vectorized adjacency + connected components
    components = _build_adjacency_components(active_items, threshold_km)
            
    # Step 3: Merge each component into a single payload
    merged_payloads = []
    for component in components:
        # Use the first item as the lead (arbitrary but consistent)
        lead_idx = component[0]
        lead_item = active_items[lead_idx]
        base_data = dict(lead_item["ev"]["data"])
        base_data["id"] = lead_item["eid"] # Ensure the broadcast ID is stable
        category = base_data.get("category")
        
        merged_all_cities = list(base_data.get("all_cities", []))
        merged_clusters = list(base_data.get("clusters", []))
        merged_trajectories = list(base_data.get("trajectories", []))
        merged_origins = list(base_data.get("highlight_origins", []))
        
        existing_city_names = {c['name'] for c in merged_all_cities if c.get('name')}
        
        for other_idx in component[1:]:
            other_data = active_items[other_idx]["ev"]["data"]
            
            # Merge unique cities
            for c in other_data.get("all_cities", []):
                if c.get('name') and c['name'] not in existing_city_names:
                    merged_all_cities.append(c)
                    existing_city_names.add(c['name'])
            
            # Aggregate visual overlays (trajectories/origins)
            merged_trajectories.extend(other_data.get("trajectories", []))
            merged_origins.extend(other_data.get("highlight_origins", []))
            
            # For clusters, we only extend if we're not flattening
            if category not in ["missiles", "hostileAircraftIntrusion"]:
                merged_clusters.extend(other_data.get("clusters", []))
            
        # Hardened Unification: If it's a unified category, recalculate ONE cluster
        if category in ["missiles", "hostileAircraftIntrusion"]:
            new_cnt, new_hull = recalculate_unified_metadata(merged_all_cities)
            merged_clusters = [{
                "origin": category,
                "centroid": new_cnt,
                "cities": merged_all_cities,
                "hull": new_hull
            }]
            base_data["center"] = new_cnt # Update the event-level center too
            
            # Refinement (v0.8.6): Recalculate unified trajectory for missiles
            if category == "missiles" and len(component) > 1 and engine:
                org_name, depth = engine.get_origin(merged_all_cities)
                border_entry = engine.get_projected_origin(merged_all_cities, org_name, depth=depth)
                merged_trajectories = [{
                    "origin": org_name,
                    "origin_coords": border_entry,
                    "marker_coords": engine.origins.get(org_name, border_entry),
                    "target_coords": new_cnt
                }]
            
        base_data["all_cities"] = merged_all_cities
        base_data["clusters"] = merged_clusters
        base_data["trajectories"] = merged_trajectories
        base_data["highlight_origins"] = merged_origins
        
        if len(component) > 1:
            logger.info(f"MERGE_DETECTED: {len(component)} events unified into one cluster (ID: {base_data['id']})")
            
        merged_payloads.append(base_data)
        
    return merged_payloads


def get_cluster_groups(active_events, threshold_km=15):
    """
    Returns a list of clusters, where each cluster is a list of event IDs
    that are merged together by the subset/proximity rules.
    
    Lightweight version of build_merged_payloads — no payload transformation,
    just adjacency grouping. Used for cluster-aware timeout synchronization.
    """
    active_items = []
    for eid, ev in active_events.items():
        if ev.get("end_time") is None:
            active_items.append({"eid": eid, "ev": ev})
    
    if not active_items:
        return []

    # Reuse the shared vectorized adjacency builder
    components = _build_adjacency_components(active_items, threshold_km)
    return [[active_items[idx]["eid"] for idx in comp] for comp in components]
