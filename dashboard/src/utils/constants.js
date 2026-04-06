// --- IRON SIGHT: Tactical Constants (FE-MODULAR-S1) ---
import TACTICAL_GEOJSON from '../assets/countries.json';
import L from 'leaflet';
import leafletIcon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

// Geographic Constants
export const ISRAEL_CENTER = [31.7683, 35.2137];
export const DEFAULT_ZOOM = window.innerWidth < 768 ? 7 : 8;


// Tactical Geodata (derived from GeoJSON at import time)
export const TACTICAL_BOUNDARIES = TACTICAL_GEOJSON.features.reduce((acc, feature) => {
  const name = feature.properties.location;
  const coords = feature.geometry.coordinates[0].map(p => [p[1], p[0]]);
  acc[name] = coords;
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

// Networking
export const IS_PROD = import.meta.env.PROD;
const RAW_HOST = import.meta.env.VITE_WS_URL || window.location.host;
const WS_HOST = RAW_HOST.replace(/^https?:\/\//, '');
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
export const WEBSOCKET_URL = `${WS_PROTOCOL}//${WS_HOST}/ws`;
export const TACTICAL_API_URL = IS_PROD ? "" : `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${WS_HOST}`;
export const MISSION_KEY = import.meta.env.VITE_MISSION_KEY;

// Tactical Color Tokens
export const TACTICAL_RED = '#ff4d4d';
export const TACTICAL_BLUE = '#4d94ff';
export const HIGHLIGHT_RED = '#ff0000';
export const HIGHLIGHT_BLUE = '#0066ff';

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
