"""Alert scope matching — mirrors dashboard/src/utils/alertMatching.js"""

import math

EXACT_MATCH_KM = 1.0
DEFAULT_RADIUS_KM = 10.0
RADIUS_MIN_KM = 3.0
RADIUS_MAX_KM = 30.0
ALLOWED_SCOPES = frozenset({"all", "radius", "exact"})


def clamp_radius_km(value):
    try:
        r = float(value)
    except (TypeError, ValueError):
        r = DEFAULT_RADIUS_KM
    return max(RADIUS_MIN_KM, min(RADIUS_MAX_KM, r))


def _haversine_km(p1, p2):
    r = 6371.0
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(point, polygon):
    if not polygon or len(polygon) < 3:
        return False
    lat, lng = point[0], point[1]
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        yi, xi = polygon[i][0], polygon[i][1]
        yj, xj = polygon[j][0], polygon[j][1]
        if (yi > lat) != (yj > lat):
            denom = yj - yi
            if abs(denom) < 1e-12:
                denom = 1e-12
            if lng < ((xj - xi) * (lat - yi)) / denom + xi:
                inside = not inside
        j = i
    return inside


def get_event_target_points(event):
    if not event:
        return []
    points = []
    seen = set()

    def add(coord):
        if not coord or len(coord) < 2:
            return
        key = f"{coord[0]:.5f},{coord[1]:.5f}"
        if key in seen:
            return
        seen.add(key)
        points.append([coord[0], coord[1]])

    for cluster in event.get("clusters") or []:
        hull = cluster.get("hull")
        if hull and len(hull) >= 2:
            for c in hull:
                add(c)
        for city in cluster.get("cities") or []:
            if isinstance(city, dict):
                add(city.get("coords"))
        add(cluster.get("centroid"))

    for c in event.get("all_cities") or []:
        if isinstance(c, dict):
            add(c.get("coords"))

    return points


def _cluster_hulls(event):
    hulls = []
    for cluster in event.get("clusters") or []:
        hull = cluster.get("hull")
        if hull and len(hull) >= 3:
            hulls.append(hull)
    return hulls


def _city_coords(event):
    coords = []
    for cluster in event.get("clusters") or []:
        for city in cluster.get("cities") or []:
            if isinstance(city, dict) and city.get("coords"):
                coords.append(city["coords"])
    for c in event.get("all_cities") or []:
        if isinstance(c, dict) and c.get("coords"):
            coords.append(c["coords"])
    return coords


def matches_alert_scope(user_location, event, scope, radius_km=None):
    if not event or event.get("category") == "newsFlash":
        return False

    if scope == "all":
        return True

    if not user_location or len(user_location) < 2:
        return False

    user = [float(user_location[0]), float(user_location[1])]

    if scope == "radius":
        radius = float(radius_km if radius_km is not None else DEFAULT_RADIUS_KM)
        points = get_event_target_points(event)
        if not points:
            return False
        return any(_haversine_km(user, p) <= radius for p in points)

    if scope == "exact":
        for hull in _cluster_hulls(event):
            if _point_in_polygon(user, hull):
                return True
        for coord in _city_coords(event):
            if _haversine_km(user, coord) <= EXACT_MATCH_KM:
                return True
        return False

    return False


def build_alert_notify_key(event):
    """Dedup key: id + city count — re-notify when more cities join same alert id."""
    city_count = len(event.get("all_cities") or [])
    return f"{event.get('id', 'unknown')}:{city_count}"


def format_push_body(event):
    cities = event.get("all_cities") or []
    names = []
    for c in cities[:4]:
        if isinstance(c, dict) and c.get("name"):
            names.append(c["name"])
        elif isinstance(c, str):
            names.append(c)
    extra = len(cities) - len(names)
    body = ", ".join(names) if names else "Active threat detected"
    if extra > 0:
        body += f" (+{extra})"
    return body
