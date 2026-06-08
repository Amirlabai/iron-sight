import { getCentroid, getConvexHull } from './geoUtils';

/**
 * When to drop per-city polygons/dots and keep cluster hulls only.
 *
 * Budget math (Leaflet + React):
 * - City boundary ring ~40 vertices → ~3KB path state per Polygon
 * - Hollow city dot → 1 Circle + optional Tooltip (~2KB fiber overhead)
 * - 500 cities ≈ 1.5MB map layer + 500 components (matches prod OOM stress band)
 * - Multi-event views stack counts: 10 salvos × 50 cities = 500
 */

/** Total city marks across visible events before suppressing detail. */
export const CITY_DETAIL_SUPPRESS_THRESHOLD = 500;

/** Multi-event: suppress earlier (80 × 6 events ≈ 480). */
export const CITY_DETAIL_MULTI_EVENT_THRESHOLD = 80;

export function isTimeFrameFilter(timeFrame) {
  return timeFrame !== 'all';
}

export function countRenderableCities(events) {
  if (!events?.length) return 0;
  let count = 0;
  for (const event of events) {
    let counted = false;
    for (const cluster of event.clusters || []) {
      for (const city of cluster.cities || []) {
        if (city?.coords || city?.boundary) count += 1;
      }
      counted = Boolean(cluster.cities?.length);
    }
    if (!counted) {
      for (const city of event.all_cities || []) {
        if (typeof city === 'object' && (city.coords || city.boundary)) count += 1;
      }
    }
  }
  return count;
}

/**
 * @param {'live' | 'archive' | 'timeframe' | 'sandbox'} viewMode
 * @param {object[] | null | undefined} events
 */
export function shouldSuppressCityDetail(viewMode, events) {
  if (viewMode === 'timeframe') return true;
  if (!events?.length) return false;

  const cityCount = countRenderableCities(events);
  const eventCount = events.length;

  if (eventCount > 1 && cityCount >= CITY_DETAIL_SUPPRESS_THRESHOLD) return true;
  if (eventCount > 1 && cityCount >= CITY_DETAIL_MULTI_EVENT_THRESHOLD) return true;
  if (eventCount === 1 && cityCount >= CITY_DETAIL_SUPPRESS_THRESHOLD) return true;

  return false;
}

function clusterCityCoords(cluster) {
  const coords = [];
  for (const city of cluster?.cities || []) {
    if (city?.coords?.length >= 2) coords.push(city.coords);
  }
  return coords;
}

function hydrateCluster(cluster) {
  if (cluster?.hull?.length > 2) return cluster;

  const coords = clusterCityCoords(cluster);
  if (cluster?.centroid?.length >= 2) coords.push(cluster.centroid);
  if (coords.length < 2) return cluster;

  const hull = getConvexHull(coords);
  const centroid = cluster.centroid?.length >= 2 ? cluster.centroid : getCentroid(coords);
  return {
    ...cluster,
    hull: hull?.length > 2 ? hull : cluster.hull,
    centroid,
  };
}

function buildClusterFromAllCities(event) {
  const cities = (event.all_cities || []).filter(
    (c) => typeof c === 'object' && c?.coords?.length >= 2,
  );
  if (cities.length < 2) return null;

  const coords = cities.map((c) => c.coords);
  const origin = event.trajectories?.[0]?.origin
    || event.clusters?.[0]?.origin
    || 'unknown';
  const hull = getConvexHull(coords);
  if (!hull || hull.length < 3) return null;

  return {
    origin,
    cities,
    hull,
    centroid: getCentroid(coords),
  };
}

/** Slim list rows lack stored hulls — synthesize from city coords for map display. */
export function hydrateEventsForMap(events) {
  if (!events?.length) return [];

  return events.map((event) => {
    let clusters = (event.clusters || []).map(hydrateCluster);
    const hasFootprint = clusters.some((c) => c.hull?.length > 2);
    if (!hasFootprint) {
      const fallback = buildClusterFromAllCities(event);
      if (fallback) clusters = [fallback];
    }
    if (clusters === event.clusters) return event;
    return { ...event, clusters };
  });
}
