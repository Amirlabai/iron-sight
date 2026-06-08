"""Slim history rows for list/pagination — full geometry loaded on demand."""

HISTORY_LIST_PROJECTION = {
    "_id": 0,
    "id": 1,
    "category": 1,
    "title": 1,
    "time": 1,
    "visual_config": 1,
    "center": 1,
    "verified": 1,
    "mergedCount": 1,
    "lifecycle_status": 1,
    "all_cities.name": 1,
    "all_cities.area": 1,
    "trajectories.origin": 1,
    "trajectories.origin_coords": 1,
    "trajectories.marker_coords": 1,
    "clusters.origin": 1,
    "clusters.centroid": 1,
    "clusters.cities.name": 1,
    "clusters.cities.coords": 1,
}


def _first_origin(doc):
    trajectories = doc.get("trajectories") or []
    if trajectories and trajectories[0].get("origin"):
        return trajectories[0]["origin"]
    clusters = doc.get("clusters") or []
    if clusters and clusters[0].get("origin"):
        return clusters[0]["origin"]
    return None


def slim_history_record(doc):
    """Strip heavy geometry; keep sidebar list + origin filter fields."""
    if not doc:
        return doc
    cities = doc.get("all_cities") or []
    slim_cities = []
    for city in cities:
        if isinstance(city, str):
            slim_cities.append({"name": city, "area": "Other"})
            continue
        if not isinstance(city, dict):
            continue
        slim_cities.append({
            "name": city.get("name"),
            "area": city.get("area", "Other"),
        })

    slim_trajectories = []
    for traj in doc.get("trajectories") or []:
        if not isinstance(traj, dict) or not traj.get("origin"):
            continue
        entry = {"origin": traj["origin"]}
        if traj.get("origin_coords"):
            entry["origin_coords"] = traj["origin_coords"]
        if traj.get("marker_coords"):
            entry["marker_coords"] = traj["marker_coords"]
        slim_trajectories.append(entry)
        break

    slim_clusters = []
    for cluster in doc.get("clusters") or []:
        if not isinstance(cluster, dict):
            continue
        slim_cluster = {"origin": cluster.get("origin"), "cities": [], "centroid": cluster.get("centroid")}
        for city in cluster.get("cities") or []:
            if isinstance(city, str):
                slim_cluster["cities"].append(city)
            elif isinstance(city, dict) and city.get("name"):
                city_entry = {"name": city["name"]}
                if city.get("coords"):
                    city_entry["coords"] = city["coords"]
                slim_cluster["cities"].append(city_entry)
        if slim_cluster.get("origin") or slim_cluster["cities"] or slim_cluster.get("centroid"):
            slim_clusters.append({k: v for k, v in slim_cluster.items() if v is not None})

    slim = {
        "id": doc.get("id"),
        "category": doc.get("category"),
        "title": doc.get("title"),
        "time": doc.get("time"),
        "visual_config": doc.get("visual_config"),
        "center": doc.get("center"),
        "verified": doc.get("verified"),
        "mergedCount": doc.get("mergedCount"),
        "lifecycle_status": doc.get("lifecycle_status"),
        "all_cities": slim_cities,
        "_listView": True,
    }
    if slim_trajectories:
        slim["trajectories"] = slim_trajectories
    if slim_clusters:
        slim["clusters"] = slim_clusters
    return {k: v for k, v in slim.items() if v is not None}
