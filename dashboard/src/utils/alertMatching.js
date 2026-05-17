import { getEventTargetPoints } from './mapGeometry';
import { getDistance } from './geoUtils';

export const EXACT_MATCH_KM = 1;
export const DEFAULT_RADIUS_KM = 10;
export const RADIUS_MIN_KM = 3;
export const RADIUS_MAX_KM = 30;

export { getEventTargetPoints };

function pointInPolygon(point, polygon) {
  if (!polygon || polygon.length < 3) return false;
  const [lat, lng] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [yi, xi] = polygon[i];
    const [yj, xj] = polygon[j];
    const intersect =
      yi > lat !== yj > lat &&
      lng < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-12) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function getClusterHulls(event) {
  const hulls = [];
  for (const cluster of event?.clusters || []) {
    if (cluster.hull?.length >= 3) hulls.push(cluster.hull);
  }
  return hulls;
}

function getCityCoords(event) {
  const coords = [];
  const add = (c) => {
    if (c?.coords?.length >= 2) coords.push(c.coords);
  };
  for (const cluster of event?.clusters || []) {
    for (const city of cluster.cities || []) add(typeof city === 'object' ? city : null);
  }
  for (const c of event?.all_cities || []) {
    if (!Array.isArray(c)) add(c);
  }
  return coords;
}

/**
 * @param {[number, number]} userLocation [lat, lng]
 * @param {object} event merged alert payload
 * @param {{ scope: string, radiusKm?: number }} prefs
 */
export function matchesAlertScope(userLocation, event, prefs) {
  if (!event || event.category === 'newsFlash') return false;

  const scope = prefs?.scope || 'all';
  if (scope === 'all') return true;

  if (!userLocation || userLocation.length < 2) return false;

  if (scope === 'radius') {
    const radiusKm = prefs.radiusKm ?? DEFAULT_RADIUS_KM;
    const points = getEventTargetPoints(event);
    if (points.length === 0) return false;
    return points.some((p) => getDistance(userLocation, p) <= radiusKm);
  }

  if (scope === 'exact') {
    for (const hull of getClusterHulls(event)) {
      if (pointInPolygon(userLocation, hull)) return true;
    }
    for (const coord of getCityCoords(event)) {
      if (getDistance(userLocation, coord) <= EXACT_MATCH_KM) return true;
    }
    return false;
  }

  return false;
}

export function filterEventsByScope(events, userLocation, prefs) {
  if (!events?.length) return [];
  if (!prefs || prefs.scope === 'all') {
    return events.filter((e) => e.category !== 'newsFlash');
  }
  return events.filter((e) => matchesAlertScope(userLocation, e, prefs));
}

/** Dedup key: id + city count — re-notify when more cities join same alert id. */
export function buildAlertNotifyKey(event) {
  const cityCount = event?.all_cities?.length ?? 0;
  return `${event?.id || 'unknown'}:${cityCount}`;
}
