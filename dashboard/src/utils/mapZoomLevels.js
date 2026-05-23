import { getDefaultZoom, STRATEGIC_METADATA } from './constants';

export const MAP_ZOOM_MIN = 4;
export const MAP_ZOOM_MAX = 14;

const INTERNAL_ORIGINS = new Set([
  'Israel',
  'terroristInfiltration',
  'hostileAircraftIntrusion',
  'missiles',
  'earthQuake',
  'unknown',
  'Unknown',
  'newsFlash',
]);

const CATEGORY_DEFAULT_ZOOM = {
  missiles: 8,
  hostileAircraftIntrusion: 10,
  terroristInfiltration: 10,
  earthQuake: 8,
  newsFlash: 8,
};

export const ORIGIN_FILTER_OPTIONS = Object.keys(STRATEGIC_METADATA)
  .filter((name) => name !== 'Israel' && !INTERNAL_ORIGINS.has(name))
  .sort();

function buildDefaultMapZoomLevels() {
  const levels = {
    overview: getDefaultZoom(),
    ...CATEGORY_DEFAULT_ZOOM,
  };
  for (const name of ORIGIN_FILTER_OPTIONS) {
    levels[`origin:${name}`] = STRATEGIC_METADATA[name]?.zoom ?? getDefaultZoom();
  }
  return levels;
}

export const DEFAULT_MAP_ZOOM_LEVELS = buildDefaultMapZoomLevels();

export function clampZoomLevel(value) {
  const n = Math.round(Number(value));
  if (Number.isNaN(n)) return getDefaultZoom();
  return Math.min(MAP_ZOOM_MAX, Math.max(MAP_ZOOM_MIN, n));
}

/** @param {Record<string, number> | null | undefined} custom */
export function mergeMapZoomLevels(custom) {
  if (!custom || typeof custom !== 'object') return { ...DEFAULT_MAP_ZOOM_LEVELS };
  const merged = { ...DEFAULT_MAP_ZOOM_LEVELS };
  for (const [key, value] of Object.entries(custom)) {
    if (typeof value === 'number' && !Number.isNaN(value)) {
      merged[key] = clampZoomLevel(value);
    }
  }
  return merged;
}

/** @param {string} key @param {Record<string, number> | null | undefined} levels */
export function getZoomLevel(key, levels) {
  const merged = mergeMapZoomLevels(levels);
  if (merged[key] != null) return merged[key];
  return merged.overview ?? getDefaultZoom();
}

/** @param {string | null | undefined} origin */
export function normalizeOriginName(origin) {
  if (!origin) return null;
  if (origin === 'North Iran') return 'Iran';
  return origin;
}

/** @param {string | null | undefined} origin @param {Record<string, number> | null | undefined} levels */
export function zoomForOrigin(origin, levels) {
  const name = normalizeOriginName(origin) || origin;
  if (!name) return getZoomLevel('overview', levels);
  return getZoomLevel(`origin:${name}`, levels);
}

/** @param {string | null | undefined} category @param {Record<string, number> | null | undefined} levels */
export function zoomForCategory(category, levels) {
  if (category && CATEGORY_DEFAULT_ZOOM[category] != null) {
    return getZoomLevel(category, levels);
  }
  return getZoomLevel('overview', levels);
}

export const MAP_ZOOM_LEVEL_ENTRIES = [
  { key: 'overview', label: 'Israel overview (multi-origin)' },
  { key: 'missiles', label: 'Missiles' },
  { key: 'hostileAircraftIntrusion', label: 'Drones' },
  { key: 'terroristInfiltration', label: 'Infiltration' },
  { key: 'earthQuake', label: 'Earthquake' },
  ...ORIGIN_FILTER_OPTIONS.map((name) => ({
    key: `origin:${name}`,
    label: name,
  })),
];

export const MAP_ZOOM_LEVEL_LABELS = Object.fromEntries(
  MAP_ZOOM_LEVEL_ENTRIES.map(({ key, label }) => [key, label]),
);

/** Panel layout rows within each section. */
export const MAP_ZOOM_LEVEL_SECTIONS = [
  {
    id: 'israel',
    title: 'Israel',
    groups: [['overview']],
  },
  {
    id: 'alerts',
    title: 'Alert type',
    groups: [
      ['missiles', 'hostileAircraftIntrusion'],
      ['terroristInfiltration', 'earthQuake'],
    ],
  },
  {
    id: 'origin',
    title: 'Launch origin',
    groups: [ORIGIN_FILTER_OPTIONS.map((name) => `origin:${name}`)],
  },
];

export function getAllMapZoomLevelKeys() {
  return MAP_ZOOM_LEVEL_SECTIONS.flatMap((section) => section.groups.flat());
}

/**
 * Commit zoom draft on blur/close. Values below min revert to fallback (avoids
 * snapping "1" to 4 while typing "10"). Out-of-range high values clamp to max.
 * @param {string} raw @param {number} fallback
 */
export function parseZoomDraft(raw, fallback) {
  const trimmed = String(raw ?? '').trim();
  if (trimmed === '') return clampZoomLevel(fallback);
  if (!/^\d+$/.test(trimmed)) return clampZoomLevel(fallback);
  const n = Number(trimmed);
  if (Number.isNaN(n)) return clampZoomLevel(fallback);
  if (n > MAP_ZOOM_MAX) return MAP_ZOOM_MAX;
  if (n < MAP_ZOOM_MIN) return clampZoomLevel(fallback);
  return n;
}
