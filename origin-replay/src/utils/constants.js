export const ISRAEL_CENTER = [31.7683, 35.2137];
export const DEFAULT_ZOOM = window.innerWidth < 768 ? 7 : 8;

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
