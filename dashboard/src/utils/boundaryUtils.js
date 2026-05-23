/** @typedef {import('leaflet').LatLngExpression[]} LatLngRing */
/** @typedef {LatLngRing | LatLngRing[]} TacticalBoundary */

/** True when boundary is [outerRing, ...holeRings] (each ring is [lat, lng][]). */
export function isBoundaryWithHoles(boundary) {
  if (!Array.isArray(boundary) || boundary.length === 0) return false;
  const first = boundary[0];
  return Array.isArray(first) && first.length > 0 && Array.isArray(first[0]);
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
