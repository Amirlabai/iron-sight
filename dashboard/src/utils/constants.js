// --- IRON SIGHT: Tactical Constants (FE-MODULAR-S1) ---
// Mobile shell semantics: see .context/MOBILE_SHELL_SPEC.md before changing breakpoints/peek.
import TACTICAL_GEOJSON from '../assets/countries.json';
import L from 'leaflet';
export {
  isBoundaryWithHoles,
  flattenBoundary,
  getBoundaryHoles,
  getBoundaryOuter,
} from './boundaryUtils';
import leafletIcon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

// Geographic Constants
export const ISRAEL_CENTER = [31.7683, 35.2137];
export const MOBILE_LAYOUT_BREAKPOINT = 1024;
export const MOBILE_SIDEBAR_HEIGHT_RATIO = 0.88;
/** Collapsed bottom-sheet peek — drag handle only (tabs hidden until expanded). */
export const MOBILE_SIDEBAR_PEEK_PX = 44;

/** Live/idle map zoom — aligned to mobile shell breakpoint (no zoom 6). */
export const getDefaultZoom = () => 8;

export const DEFAULT_ZOOM = getDefaultZoom();

/** Overview zoom when browsing history by timeframe (8 — mobile previously used 6, too wide). */
export const getTimeframeOverviewZoom = () => 8;


function ringsFromPolygonCoords(polygonCoords) {
  const rings = polygonCoords.map((ring) => ring.map((p) => [p[1], p[0]]));
  return rings.length === 1 ? rings[0] : rings;
}

function geoJsonToBoundary(feature) {
  const { type, coordinates } = feature.geometry;
  if (type === 'Polygon') {
    return ringsFromPolygonCoords(coordinates);
  }
  if (type === 'MultiPolygon') {
    return ringsFromPolygonCoords(coordinates[0] ?? []);
  }
  return [];
}

// Tactical Geodata (derived from GeoJSON at import time)
export const TACTICAL_BOUNDARIES = TACTICAL_GEOJSON.features.reduce((acc, feature) => {
  const name = feature.properties.location;
  acc[name] = geoJsonToBoundary(feature);
  return acc;
}, {});

export const STRATEGIC_METADATA = TACTICAL_GEOJSON.features.reduce((acc, feature) => {
  acc[feature.properties.location] = {
    depth: feature.properties.depth,
    zoom: feature.properties["zoom level"],
    color: feature.properties.color
  };
  return acc;
}, {});

// Networking — dev uses Vite origin + proxy. Prod: REST via Vercel /api rewrite; WS direct to Render
// (Vercel edge does not reliably proxy WebSocket upgrades on /ws — GET /ws returns index.html).
export const IS_PROD = import.meta.env.PROD;
const PROD_WS_HOST = 'iron-sight-hjwf.onrender.com';

function normalizeHost(raw) {
  return String(raw || '').replace(/^https?:\/\//, '').replace(/\/+$/, '');
}

const WS_HOST = IS_PROD
  ? normalizeHost(import.meta.env.VITE_WS_URL || PROD_WS_HOST)
  : window.location.host;
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
export const WEBSOCKET_URL = `${WS_PROTOCOL}//${WS_HOST}/ws`;
export const TACTICAL_API_URL = IS_PROD ? '' : `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${window.location.host}`;
export const MISSION_KEY = import.meta.env.VITE_MISSION_KEY;

// Tactical Color Tokens
export const TACTICAL_RED = '#ff4d4d';
export const TACTICAL_BLUE = '#4d94ff';
export const HIGHLIGHT_RED = '#ff0000';
export const HIGHLIGHT_BLUE = '#0066ff';

/** Category urgency colors — aligned with :root CSS vars */
export const CATEGORY_COLORS = {
  missiles: '#ff3b30',
  hostileAircraftIntrusion: '#ff9500',
  terroristInfiltration: '#b518ff',
  earthQuake: '#4cd964',
  newsFlash: 'rgba(255,255,255,0.35)',
};

export const categoryTint = (color, percent = 8) =>
  `color-mix(in srgb, ${color} ${percent}%, transparent)`;

// Audio Singleton State (module-level globals)
export const SEEN_ALERTS = new Set();
export let GLOBAL_LAST_PLAY_TIME = 0;
export const setGlobalLastPlayTime = (t) => { GLOBAL_LAST_PLAY_TIME = t; };

// Leaflet Icon Fix
export const DefaultIcon = L.icon({
  iconUrl: leafletIcon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;
