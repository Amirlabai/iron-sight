"""Kfar Kama (כפר כמא) alert detection for Telegram notifications."""

import math

from src.utils.config import KFAR_KAMA_ALERT_LAT, KFAR_KAMA_ALERT_LNG
from src.utils.text_utils import standardize_name

KFAR_KAMA_CITY_ID = 1235
KFAR_KAMA_COORDS = (KFAR_KAMA_ALERT_LAT, KFAR_KAMA_ALERT_LNG)

# Trajectory endpoints only (no city name on path). Not used for all_cities proximity.
TRAJECTORY_ENDPOINT_NEAR_M = 800

_KFAR_KAMA_STD_NAMES = frozenset({
    standardize_name("כפר כמא"),
    standardize_name("Kfar Kama"),
    standardize_name("kfar kama"),
})

_EARTH_RADIUS_M = 6371000


def _haversine_meters(p1, p2) -> float:
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _coord_near_kfar_kama(coord, max_m: float = TRAJECTORY_ENDPOINT_NEAR_M) -> bool:
    if not coord or len(coord) < 2:
        return False
    try:
        return _haversine_meters(coord, KFAR_KAMA_COORDS) <= max_m
    except (TypeError, ValueError):
        return False


def is_kfar_kama_city(city) -> bool:
    """Match by city_id or standardized name only (not coord proximity)."""
    if not city:
        return False
    if isinstance(city, str):
        return standardize_name(city) in _KFAR_KAMA_STD_NAMES
    if not isinstance(city, dict):
        return False
    if city.get("city_id") == KFAR_KAMA_CITY_ID:
        return True
    name = city.get("name")
    return bool(name and standardize_name(name) in _KFAR_KAMA_STD_NAMES)


def event_affects_kfar_kama(event) -> bool:
    if not event:
        return False
    for city in event.get("all_cities") or []:
        if is_kfar_kama_city(city):
            return True
    for cluster in event.get("clusters") or []:
        for city in cluster.get("cities") or []:
            if is_kfar_kama_city(city):
                return True
    for traj in event.get("trajectories") or []:
        if not isinstance(traj, dict):
            continue
        for key in ("origin_coords", "target_coords", "marker_coords"):
            if _coord_near_kfar_kama(traj.get(key)):
                return True
    for origin in event.get("highlight_origins") or []:
        if isinstance(origin, dict):
            if is_kfar_kama_city(origin.get("name")):
                return True
        elif is_kfar_kama_city(origin):
            return True
    return False


def event_track_ids(event, alert_id=None) -> set[str]:
    """Merged master id plus sibling ids for START/END correlation."""
    ids = set()
    if alert_id:
        ids.add(alert_id)
    if event:
        eid = event.get("id")
        if eid:
            ids.add(eid)
        for mid in event.get("merged_ids") or []:
            if mid:
                ids.add(mid)
    return ids


def collect_broadcast_track_ids(events_list) -> set[str]:
    ids: set[str] = set()
    for event in events_list or []:
        ids.update(event_track_ids(event))
    return ids


def collect_active_track_ids(events_list, active_events=None) -> set[str]:
    """Broadcast merged ids plus live (non-ended) raw active_events keys.

    Ended events drop out of merged broadcast payloads before purge; including
    still-active raw ids avoids clearing dedup state too early.
    """
    ids = collect_broadcast_track_ids(events_list)
    if active_events:
        ids.update(
            aid for aid, ev in active_events.items()
            if ev.get("end_time") is None
        )
    return ids
