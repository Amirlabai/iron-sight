import { calculateBestMapConfig } from './mapGeometry';
import {
  mergeMapZoomLevels,
  normalizeOriginName,
} from './mapZoomLevels';

export {
  MAP_ZOOM_MIN,
  MAP_ZOOM_MAX,
  DEFAULT_MAP_ZOOM_LEVELS,
  mergeMapZoomLevels,
  clampZoomLevel,
  getZoomLevel,
  normalizeOriginName,
  ORIGIN_FILTER_OPTIONS,
  MAP_ZOOM_LEVEL_ENTRIES,
} from './mapZoomLevels';

/** @param {object | null | undefined} event */
export function getEventOrigin(event) {
  const raw = event?.trajectories?.[0]?.origin || event?.clusters?.[0]?.origin;
  return normalizeOriginName(raw);
}

/**
 * Live map framing uses automatic logic with user zoom numbers from preferences.
 * @param {object[]} events
 * @param {{ mapZoomLevels?: Record<string, number> }} prefs
 */
export function resolveMapConfig(events, { mapZoomLevels } = {}) {
  return calculateBestMapConfig(events, mergeMapZoomLevels(mapZoomLevels));
}
