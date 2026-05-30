/**
 * Hex colors for Leaflet canvas paths (CSS variables are not resolved on canvas).
 */
import { STRATEGIC_METADATA } from './constants';

export const CATEGORY_HEX = {
  missiles: '#ff3b30',
  hostileAircraftIntrusion: '#ff9500',
  terroristInfiltration: '#bf5af2',
  earthQuake: '#64d2ff',
  newsFlash: '#ffcc00',
};

/**
 * @param {object} event
 * @param {string} fallback
 * @param {{ origin?: string } | null} item
 */
export function resolveCanvasColor(event, fallback, item = null) {
  const fromConfig = event?.visual_config?.color;
  if (typeof fromConfig === 'string' && fromConfig.startsWith('#')) {
    return fromConfig;
  }
  if (event?.category && CATEGORY_HEX[event.category]) {
    return CATEGORY_HEX[event.category];
  }
  const origin = item?.origin;
  if (origin && STRATEGIC_METADATA[origin]?.color) {
    return STRATEGIC_METADATA[origin].color;
  }
  if (typeof fallback === 'string' && fallback.startsWith('#')) {
    return fallback;
  }
  return CATEGORY_HEX.missiles;
}

/**
 * Color for divIcon HTML (must be hex or rgb, not var(--token)).
 */
export function resolveMarkerColor(event, fallback, item = null) {
  return resolveCanvasColor(event, fallback, item);
}
