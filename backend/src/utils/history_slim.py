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
    "clusters.origin": 1,
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

    origin = _first_origin(doc)
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
    if origin:
        slim["trajectories"] = [{"origin": origin}]
    return {k: v for k, v in slim.items() if v is not None}
