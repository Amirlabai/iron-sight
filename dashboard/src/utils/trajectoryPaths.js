/**
 * Arc-length path math for tactical motion (missiles + drones).
 */

export const MISSILE_SPEED_MPS = 20000;
export const DRONE_SPEED_MPS = 6000;
export const MEET_FRACTION = 0.80;
export const HOLD_MS = 550;
export const INTERCEPTOR_COUNT = 3;
export const MIN_MISSILE_LOOP_MS = 1000;

const EARTH_RADIUS_M = 6371000;

/** Minimum on-screen speed so sprites move visibly at country zoom (6–8). */
export const MIN_SCREEN_PX_PER_SEC = 100;

export function roundCoordKey(lat, lng, decimals = 4) {
  const factor = 10 ** decimals;
  return `${Math.round(lat * factor) / factor},${Math.round(lng * factor) / factor}`;
}

/** Web-Mercator meters per pixel at latitude (256 px tiles). */
export function metersPerPixel(zoom, latitude) {
  const latRad = (latitude * Math.PI) / 180;
  return (40075016.686 * Math.cos(latRad)) / 2 ** (zoom + 8);
}

/**
 * Ground speed that guarantees at least MIN_SCREEN_PX_PER_SEC on screen.
 */
export function visibleMetersPerSecond(baseMps, zoom, latitude) {
  const mpp = metersPerPixel(zoom, latitude);
  return Math.max(baseMps, MIN_SCREEN_PX_PER_SEC * mpp);
}

/**
 * Speed for a path segment: visible on screen and completes arc within maxDurationSec.
 */
export function motionSpeedMps(baseMps, zoom, latitude, arcMeters, maxDurationSec) {
  const visible = visibleMetersPerSecond(baseMps, zoom, latitude);
  if (!arcMeters || arcMeters <= 0 || !maxDurationSec || maxDurationSec <= 0) {
    return visible;
  }
  const minForDuration = arcMeters / maxDurationSec;
  return Math.max(visible, minForDuration);
}

export function haversineMeters(p1, p2) {
  const lat1 = (p1[0] * Math.PI) / 180;
  const lat2 = (p2[0] * Math.PI) / 180;
  const dLat = lat2 - lat1;
  const dLng = ((p2[1] - p1[1]) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a));
}

export function lerpCoord(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

export function buildMainPath(origin, target, steps = 64) {
  const path = [];
  for (let i = 0; i <= steps; i += 1) {
    path.push(lerpCoord(origin, target, i / steps));
  }
  return path;
}

export function buildCumulativeDistances(path) {
  const cumDist = [0];
  for (let i = 1; i < path.length; i += 1) {
    cumDist.push(cumDist[i - 1] + haversineMeters(path[i - 1], path[i]));
  }
  return cumDist;
}

export function pathLengthMeters(path) {
  const cum = buildCumulativeDistances(path);
  return cum[cum.length - 1];
}

export function positionAtArcDistance(path, cumDist, distance) {
  if (!path?.length) return null;
  if (distance <= 0) return [...path[0]];
  const total = cumDist[cumDist.length - 1];
  if (distance >= total) return [...path[path.length - 1]];

  let i = 1;
  while (i < cumDist.length && cumDist[i] < distance) i += 1;
  const d0 = cumDist[i - 1];
  const d1 = cumDist[i];
  const segLen = d1 - d0;
  const t = segLen > 0 ? (distance - d0) / segLen : 0;
  return lerpCoord(path[i - 1], path[i], t);
}

/** Initial bearing p1→p2: degrees clockwise from north (0–360). */
export function bearingBetween(p1, p2) {
  const lat1 = (p1[0] * Math.PI) / 180;
  const lat2 = (p2[0] * Math.PI) / 180;
  const dLng = ((p2[1] - p1[1]) * Math.PI) / 180;
  const y = Math.sin(dLng) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
  const deg = (Math.atan2(y, x) * 180) / Math.PI;
  return (deg + 360) % 360;
}

/**
 * Map sprite contract: unrotated PNG top edge = forward (nose).
 * bearing = clockwise degrees from screen up (from screenBearingBetween on the map).
 * Assets must be authored nose-up; tune offset only if art cannot be re-exported.
 */
export const SPRITE_HEADING_OFFSET_DEG = 0;

export function spriteCssRotation(screenBearingDeg) {
  return (screenBearingDeg + SPRITE_HEADING_OFFSET_DEG + 360) % 360;
}

/**
 * Rotation only — centering is Leaflet iconAnchor margins + .motion-sprite-wrap flex.
 * Optional scale (drone zoom) applied before rotate; transform-origin on sprite.
 */
export function motionSpriteTransformCss(screenBearingDeg, { scale = 1 } = {}) {
  const deg = spriteCssRotation(screenBearingDeg);
  if (scale !== 1) return `scale(${scale}) rotate(${deg}deg)`;
  return `rotate(${deg}deg)`;
}

export function quadraticBezier(a, control, b, t) {
  const u = 1 - t;
  return [
    u * u * a[0] + 2 * u * t * control[0] + t * t * b[0],
    u * u * a[1] + 2 * u * t * control[1] + t * t * b[1],
  ];
}

/** Interceptor arc: launch at target, bulge sideways mid-flight, meet inbound rocket. */
export function buildInterceptorFanPath(launch, meet, perpLat, perpLng, offsetSign, fanScale) {
  const base = buildMainPath(launch, meet, 40);
  const maxBulge = 0.035 * fanScale * offsetSign;
  return base.map((pt, i) => {
    if (i === 0) return [...launch];
    if (i === base.length - 1) return [...meet];
    const t = i / (base.length - 1);
    const bulge = Math.sin(t * Math.PI) * maxBulge;
    return [pt[0] + perpLat * bulge, pt[1] + perpLng * bulge];
  });
}

/**
 * @param {[number, number]} origin
 * @param {[number, number]} target
 */
export function buildInterceptPlan(origin, target, options = {}) {
  const speedMps = options.speedMps ?? MISSILE_SPEED_MPS;
  const meetFraction = options.meetFraction ?? MEET_FRACTION;
  const interceptorCount = options.interceptorCount ?? INTERCEPTOR_COUNT;

  const fullPath = buildMainPath(origin, target, 64);
  const meetIndex = Math.max(
    1,
    Math.min(fullPath.length - 1, Math.floor(fullPath.length * meetFraction)),
  );
  const mainPathToMeet = fullPath.slice(0, meetIndex + 1);
  const meetPoint = [...mainPathToMeet[mainPathToMeet.length - 1]];
  const cumDistMain = buildCumulativeDistances(mainPathToMeet);
  const mainArcM = cumDistMain[cumDistMain.length - 1];
  const mainTimeToMeet = mainArcM / speedMps;

  const inboundBearing = bearingBetween(origin, meetPoint);
  const perpDeg = inboundBearing + 90;
  const perpRad = (perpDeg * Math.PI) / 180;
  const perpLat = Math.cos(perpRad) * 0.06;
  const perpLng = Math.sin(perpRad) * 0.06;

  const interceptorPaths = [];
  const intArcM = [];
  const cumDistInt = [];
  const maxIntArcM = mainArcM * 0.98;

  for (let i = 0; i < interceptorCount; i += 1) {
    const fanScale = 15 + i * 0.25;
    const offsetSign = i === 1 ? 0 : i === 0 ? -1 : 1;
    const path = buildInterceptorFanPath(target, meetPoint, perpLat, perpLng, offsetSign, fanScale);
    const cum = buildCumulativeDistances(path);
    const arcM = Math.min(cum[cum.length - 1], maxIntArcM);

    interceptorPaths.push(path);
    cumDistInt.push(cum);
    intArcM.push(arcM);
  }

  return {
    mainPathToMeet,
    meetPoint,
    mainArcM,
    mainTimeToMeet,
    cumDistMain,
    interceptorPaths,
    intArcM,
    cumDistInt,
    speedMps,
  };
}

/** Closed polyline positions for map display (first point repeated at end). */
export function closeWaypointPath(waypoints) {
  if (!waypoints?.length) return [];
  if (waypoints.length < 2) return [...waypoints];
  const first = waypoints[0];
  const last = waypoints[waypoints.length - 1];
  if (first[0] === last[0] && first[1] === last[1]) {
    return waypoints.map((w) => [w[0], w[1]]);
  }
  return [...waypoints.map((w) => [w[0], w[1]]), [first[0], first[1]]];
}

/**
 * @param {Array<[number, number]>} waypoints
 */
export function buildWaypointLoopPlan(waypoints, options = {}) {
  const closeLoop = options.closeLoop !== false;
  const speedMps = options.speedMps ?? DRONE_SPEED_MPS;

  let path = waypoints
    .filter((c) => c && c.length >= 2)
    .map((c) => [c[0], c[1]]);

  if (path.length < 2) return null;

  if (closeLoop) {
    path = [...path, [path[0][0], path[0][1]]];
  }

  const cumDist = buildCumulativeDistances(path);
  const totalArcM = cumDist[cumDist.length - 1];
  if (totalArcM <= 0) return null;

  return {
    path,
    totalArcM,
    cumDist,
    speedMps,
    loopPeriod: totalArcM / speedMps,
  };
}

/**
 * @param {(from: [number, number], to: [number, number]) => number} bearingFn
 *   Geographic bearing by default. Map sprites: pass (a,b) => screenBearingBetween(map,a,b)
 *   so tangent matches the drawn path (not necessarily geographic north).
 */
export function positionAndBearingAtDistance(
  path,
  cumDist,
  distance,
  bearingFn = bearingBetween,
) {
  const pos = positionAtArcDistance(path, cumDist, distance);
  if (!pos) return null;

  const total = cumDist[cumDist.length - 1];
  if (total <= 0) return { pos, bearing: 0 };

  const eps = Math.max(80, total * 0.03);
  let bearing;
  if (distance + eps < total) {
    const posAhead = positionAtArcDistance(path, cumDist, distance + eps);
    bearing = bearingFn(pos, posAhead);
  } else if (distance > eps) {
    const posBehind = positionAtArcDistance(path, cumDist, distance - eps);
    bearing = bearingFn(posBehind, pos);
  } else {
    const posAhead = positionAtArcDistance(path, cumDist, Math.min(eps, total));
    bearing = bearingFn(pos, posAhead);
  }

  return { pos, bearing };
}
