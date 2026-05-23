/** @typedef {import('leaflet').LatLngExpression[]} LatLngRing */
/** @typedef {LatLngRing | LatLngRing[]} TacticalBoundary */

function isLatLngPair(node) {
  return (
    Array.isArray(node) &&
    node.length >= 2 &&
    typeof node[0] === 'number' &&
    typeof node[1] === 'number' &&
    !Number.isNaN(node[0]) &&
    !Number.isNaN(node[1])
  );
}

/** True when boundary is [outerRing, ...holeRings] (each ring is [lat, lng][]). */
export function isBoundaryWithHoles(boundary) {
  if (!Array.isArray(boundary) || boundary.length < 2) return false;
  const first = boundary[0];
  return (
    Array.isArray(first) &&
    first.length > 0 &&
    !isLatLngPair(first) &&
    isLatLngPair(first[0])
  );
}

/** All rings flattened to a single point list (for bounds / centroid). */
export function flattenBoundary(boundary) {
  if (!boundary?.length) return [];
  if (isBoundaryWithHoles(boundary)) {
    return boundary.flat();
  }
  return boundary;
}

/** Hole rings only (empty when simple polygon). */
export function getBoundaryHoles(boundary) {
  return isBoundaryWithHoles(boundary) ? boundary.slice(1) : [];
}

/** Outer ring for simple or cutout boundaries. */
export function getBoundaryOuter(boundary) {
  if (!boundary?.length) return [];
  return isBoundaryWithHoles(boundary) ? boundary[0] : boundary;
}
