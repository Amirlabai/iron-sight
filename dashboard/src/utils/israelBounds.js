import { TACTICAL_BOUNDARIES } from './constants';
import { getBoundaryOuter, getBoundaryHoles } from './boundaryUtils';
import { pointInPolygon } from './geoPolygon';

const ISRAEL_BOUNDARY = TACTICAL_BOUNDARIES['Israel'];

/**
 * True when [lat, lng] is inside Israel outer ring and not inside a boundary hole.
 * @param {[number, number]} point
 */
export function isLocationInIsrael(point) {
  if (!point || point.length < 2) return false;
  const outer = getBoundaryOuter(ISRAEL_BOUNDARY);
  if (!pointInPolygon(point, outer)) return false;
  for (const hole of getBoundaryHoles(ISRAEL_BOUNDARY)) {
    if (pointInPolygon(point, hole)) return false;
  }
  return true;
}
