import math
import logging
import numpy as np
from scipy.spatial import ConvexHull

logger = logging.getLogger("IronSightClustering")

def haversine_distance(coord1, coord2):
    """Calculate the great circle distance in kilometers between two points on the earth."""
    if not coord1 or not coord2:
        return float('inf')
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0 # Radius of earth in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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

    # Step 1: Build an adjacency list of mergable items
    adj = {i: set() for i in range(len(active_items))}
    for i in range(len(active_items)):
        for j in range(i + 1, len(active_items)):
            item_a = active_items[i]
            item_b = active_items[j]
            
            # Same category check
            if item_a["ev"].get("category") != item_b["ev"].get("category"):
                continue
                
            cities_a = item_a["ev"]["data"].get("all_cities", [])
            cities_b = item_b["ev"]["data"].get("all_cities", [])
            
            # Subset Rule
            subset_match = is_subset(cities_a, cities_b) or is_subset(cities_b, cities_a)
            
            # Proximity Rule
            center_a = item_a["ev"]["data"].get("center")
            center_b = item_b["ev"]["data"].get("center")
            proximate_match = False
            if center_a and center_b:
                if haversine_distance(center_a, center_b) <= threshold_km:
                    proximate_match = True
            
            if subset_match or proximate_match:
                adj[i].add(j)
                adj[j].add(i)
                
    # Step 2: Find connected components (groups)
    visited = set()
    components = []
    for i in range(len(active_items)):
        if i not in visited:
            stack = [i]
            component = []
            while stack:
                node = stack.pop()
                if node not in visited:
                    visited.add(node)
                    component.append(node)
                    stack.extend(adj[node] - visited)
            components.append(component)
            
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
