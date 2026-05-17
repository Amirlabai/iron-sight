import {
  ISRAEL_CENTER,
  getDefaultZoom,
  MOBILE_LAYOUT_BREAKPOINT,
  STRATEGIC_METADATA,
  TACTICAL_BOUNDARIES,
  getTimeframeOverviewZoom,
} from './constants';

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

function centroidOf(points) {
  if (!points.length) return ISRAEL_CENTER;
  const lat = points.reduce((s, p) => s + p[0], 0) / points.length;
  const lng = points.reduce((s, p) => s + p[1], 0) / points.length;
  return [lat, lng];
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

export function calculateBestMapConfig(events) {
  const base = { bounds: null, maxZoom: undefined };

  if (!events || events.length === 0) {
    return { center: ISRAEL_CENTER, zoom: getDefaultZoom(), ...base };
  }

  const allTrajectories = events.flatMap(e => e.trajectories || []);

  if (allTrajectories.length > 0) {
    const allOrigins = [
      ...allTrajectories.map(t => t.origin),
      ...events.flatMap(e => e.clusters || []).map(c => c.origin),
    ];

    const uniqueOrigins = new Set(
      allOrigins
        .filter(o => o && o !== 'Unknown' && o !== 'newsFlash')
        .map(o => (o === 'North Iran' ? 'Iran' : o))
    );

    let bestTraj = allTrajectories[0];
    let minZoom = STRATEGIC_METADATA[bestTraj.origin]?.zoom || getDefaultZoom();

    for (const traj of allTrajectories) {
      const z = STRATEGIC_METADATA[traj.origin]?.zoom || getDefaultZoom();
      if (z < minZoom) {
        minZoom = z;
        bestTraj = traj;
      }
    }

    if (uniqueOrigins.size > 1) {
      return { center: ISRAEL_CENTER, zoom: getDefaultZoom(), ...base };
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

  const withCenter = events.find(e => e.center);
  if (withCenter) {
    return {
      center: withCenter.center,
      zoom: withCenter.zoom_level || getDefaultZoom(),
      ...base,
    };
  }

  return { center: ISRAEL_CENTER, zoom: getDefaultZoom(), ...base };
}

export function calculateArchiveMapConfig(event) {
  const points = getEventTargetPoints(event);

  if (points.length >= 2) {
    return {
      center: centroidOf(points),
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
  const israelBoundary = TACTICAL_BOUNDARIES['Israel'];
  const bounds = israelBoundary?.length >= 2 ? israelBoundary : null;

  return {
    center: ISRAEL_CENTER,
    zoom: getTimeframeOverviewZoom(),
    bounds,
    maxZoom: getTimeframeOverviewZoom(),
  };
}
