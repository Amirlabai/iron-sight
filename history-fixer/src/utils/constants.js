// --- IRON SIGHT: History Fixer Constants ---

export const ISRAEL_CENTER = [31.7683, 35.2137];
export const DEFAULT_ZOOM = window.innerWidth < 768 ? 7 : 8;

export const TACTICAL_RED = '#ff4d4d';
export const TACTICAL_BLUE = '#4d94ff';
export const HIGHLIGHT_RED = '#ff0000';
export const HIGHLIGHT_BLUE = '#0066ff';

export const STRATEGIC_METADATA = {
  Gaza: { color: '#ff3b30', label: 'Gaza Strip' },
  Lebanon: { color: '#ff9500', label: 'Southern Lebanon' },
  Yemen: { color: '#ffcc00', label: 'Western Yemen' },
  Iran: { color: '#af52de', label: 'Central Iran' },
  'North Iran': { color: '#af52de', label: 'Northern Iran' },
  Iraq: { color: '#5856d6', label: 'Iraqi Frontier' },
  hostileAircraftIntrusion: { color: '#ff9500', label: 'Drone Corridor' },
};

export const IS_PROD = import.meta.env.PROD;

/**
 * Dev: always same-origin so Vite proxies /api → VITE_API_PROXY_TARGET (local 8080).
 * Do not set VITE_API_URL in dev — it bypasses the proxy and breaks local backend.
 * Production build: set VITE_API_URL to your deployed API origin.
 */
function resolveApiBase() {
  if (import.meta.env.DEV) {
    return `${window.location.protocol}//${window.location.host}`;
  }
  const explicit = import.meta.env.VITE_API_URL;
  return explicit ? String(explicit).replace(/\/$/, '') : '';
}

export const TACTICAL_API_URL = resolveApiBase();

export const API_PROXY_TARGET =
  import.meta.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8080';

export const MISSION_KEY =
  import.meta.env.VITE_MISSION_KEY || 'IS-TAC-7A2B-91C4-8E6F-D25B';

export const HISTORY_FETCH_LIMIT = 500;

export const ORIGINS_DATA = {
  Gaza: [31.4167, 34.3333],
  Lebanon: [33.8886, 35.8623],
  Yemen: [15.3547, 44.2067],
  Iran: [32.4279, 53.6880],
  Iraq: [33.3152, 44.3661],
};
