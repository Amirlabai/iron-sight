// --- IRON SIGHT: History Fixer Constants ---

export const ISRAEL_CENTER = [31.7683, 35.2137];
export const DEFAULT_ZOOM = 8;

export const TACTICAL_RED = '#ff4d4d';
export const TACTICAL_BLUE = '#4d94ff';
export const HIGHLIGHT_RED = '#ff0000';
export const HIGHLIGHT_BLUE = '#0066ff';

// Networking
export const IS_PROD = import.meta.env.PROD;
// History fixer usually runs locally against the local backend
export const TACTICAL_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
export const MISSION_KEY = 'IS-TAC-7A2B-91C4-8E6F-D25B';

export const ORIGINS_DATA = {
  "Gaza": [31.4167, 34.3333],
  "Lebanon": [33.8886, 35.8623],
  "Yemen": [15.3547, 44.2067],
  "Iran": [32.4279, 53.6880]
};
