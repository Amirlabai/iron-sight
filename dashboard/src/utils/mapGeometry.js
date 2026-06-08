import {
  ISRAEL_CENTER,
  getDefaultZoom,
  MOBILE_LAYOUT_BREAKPOINT,
  TACTICAL_BOUNDARIES,
  getTimeframeOverviewZoom,
  flattenBoundary,
  getBoundaryOuter,
} from './constants';
import { getCentroid } from './geoUtils';
import { resolveTrajectoryOrigin } from './motionEndpoints';
import { getZoomLevel, normalizeOriginName, zoomForCategory, zoomForOrigin } from './mapZoomLevels';

export function getFitPadding() {
  const isMobile = window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT;
  return {
    paddingTopLeft: [40, 40],
    paddingBottomRight: [40, isMobile ? 200 : 40],
  };
}

export function boundsKey(bounds) {
  if (!bounds?.length) return '';
  const first = bounds[0];
  const last = bounds[bounds.length - 1];
  return `${bounds.length}:${first[0]},${first[1]}:${last[0]},${last[1]}`;
}

/** Pin on map for origin border entry (same point as trajectory line start). */
export function resolveOriginPinCoords(origin, trajectory = null) {
  const fromTraj = resolveTrajectoryOrigin(trajectory);
  if (fromTraj) return fromTraj;
  const boundary = TACTICAL_BOUNDARIES[origin];
  const outer = getBoundaryOuter(boundary);
  if (outer?.length >= 2) {
    return getCentroid(outer) ?? ISRAEL_CENTER;
  }
  return null;
}

/** Collect [lat, lng] from threat footprint geometry */
export function getEventTargetPoints(event) {
  if (!event) return [];
  const points = [];
  const seen = new Set();
  const add = (coord) => {
    if (!coord || coord.length < 2) return;
    const key = `${coord[0].toFixed(5)},${coord[1].toFixed(5)}`;
    if (seen.has(key)) return;
    seen.add(key);
    points.push([coord[0], coord[1]]);
  };

  for (const cluster of event.clusters || []) {
    if (cluster.hull?.length >= 2) {
      cluster.hull.forEach(add);
    }
    for (const city of cluster.cities || []) {
      add(city.coords);
    }
    add(cluster.centroid);
  }

  for (const c of event.all_cities || []) {
    if (Array.isArray(c)) continue;
    add(c.coords);
  }

  return points;
}

/**
 * @param {object[]} events
 * @param {Record<string, number> | null | undefined} mapZoomLevels user overrides from preferences
 */
export function calculateBestMapConfig(events, mapZoomLevels = null) {
  const base = { bounds: null, maxZoom: undefined };
  const overviewZoom = getZoomLevel('overview', mapZoomLevels);

  if (!events || events.length === 0) {
    return { center: ISRAEL_CENTER, zoom: overviewZoom, ...base };
  }

  // For active missile alerts, prioritize affected target area centering over origin corridors.
  const missileEvents = events.filter((e) => e?.category === 'missiles');
  if (missileEvents.length > 0) {
    const missilePoints = missileEvents.flatMap((e) => getEventTargetPoints(e));
    if (missilePoints.length >= 2) {
      return {
        center: getCentroid(missilePoints) ?? ISRAEL_CENTER,
        zoom: zoomForCategory('missiles', mapZoomLevels),
        bounds: missilePoints,
        maxZoom: window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT ? 10 : 12,
      };
    }
    if (missilePoints.length === 1) {
      return {
        center: missilePoints[0],
        zoom: zoomForCategory('missiles', mapZoomLevels),
        ...base,
      };
    }
  }

  const allTrajectories = events.flatMap((e) => e.trajectories || []);

  if (allTrajectories.length > 0) {
    const allOrigins = [
      ...allTrajectories.map((t) => t.origin),
      ...events.flatMap((e) => e.clusters || []).map((c) => c.origin),
    ];

    const uniqueOrigins = new Set(
      allOrigins
        .filter((o) => o && o !== 'Unknown' && o !== 'newsFlash')
        .map((o) => normalizeOriginName(o)),
    );

    let bestTraj = allTrajectories[0];
    let minZoom = zoomForOrigin(bestTraj.origin, mapZoomLevels);

    for (const traj of allTrajectories) {
      const z = zoomForOrigin(traj.origin, mapZoomLevels);
      if (z < minZoom) {
        minZoom = z;
        bestTraj = traj;
      }
    }

    if (uniqueOrigins.size > 1) {
      return { center: ISRAEL_CENTER, zoom: overviewZoom, ...base };
    }

    return {
      center: [
        (bestTraj.origin_coords[0] + bestTraj.target_coords[0]) / 2,
        (bestTraj.origin_coords[1] + bestTraj.target_coords[1]) / 2,
      ],
      zoom: minZoom,
      ...base,
    };
  }

  const withCenter = events.find((e) => e.center);
  if (withCenter) {
    return {
      center: withCenter.center,
      zoom: withCenter.zoom_level || overviewZoom,
      ...base,
    };
  }

  return { center: ISRAEL_CENTER, zoom: overviewZoom, ...base };
}

export function calculateArchiveMapConfig(event) {
  const points = getEventTargetPoints(event);

  if (points.length >= 2) {
    return {
      center: getCentroid(points) ?? ISRAEL_CENTER,
      zoom: getDefaultZoom(),
      bounds: points,
      maxZoom: window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT ? 10 : 12,
    };
  }

  if (points.length === 1) {
    return {
      center: points[0],
      zoom: 10,
      bounds: null,
      maxZoom: undefined,
    };
  }

  return calculateBestMapConfig([event]);
}

export function calculateTimeframeMapConfig() {
  const flat = flattenBoundary(TACTICAL_BOUNDARIES['Israel']);
  const bounds = flat.length >= 2 ? flat : null;

  return {
    center: ISRAEL_CENTER,
    zoom: getTimeframeOverviewZoom(),
    bounds,
    maxZoom: getTimeframeOverviewZoom(),
  };
}
