import { DEFAULT_MAP_ZOOM_LEVELS } from './mapZoomLevels';

export const STORAGE_KEYS = {
  UI: 'iron_sight_prefs_ui',
  MAP: 'iron_sight_map_zoom',
  PUSH: 'iron_sight_push',
  LEGACY: 'iron_sight_alert_prefs',
};

const UI_FIELDS = [
  'complete',
  'notifyPermission',
  'geoPermission',
  'scope',
  'radiusKm',
  'wizardDismissed',
  'showUserLocationOnMap',
];

const PUSH_FIELDS = ['pushEndpoint', 'pushClientToken'];

const ALL_PARTITIONS = ['ui', 'map', 'push'];
const DEBOUNCE_MS = 300;

const lastSavedJson = { ui: null, map: null, push: null };
let debounceTimer = null;
let pendingSnapshot = null;
let pendingOptions = null;

function safeGet(storage, key) {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(storage, key, value) {
  try {
    storage.setItem(key, value);
  } catch {
    /* ignore quota / private mode */
  }
}

function safeRemove(storage, key) {
  try {
    storage.removeItem(key);
  } catch {
    /* ignore */
  }
}

function pickUi(prefs, { includeLocation = false } = {}) {
  const ui = {};
  for (const key of UI_FIELDS) {
    if (key in prefs) ui[key] = prefs[key];
  }
  if (includeLocation) {
    ui.location = prefs.location ?? null;
    ui.locationUpdatedAt = prefs.locationUpdatedAt ?? null;
  }
  return ui;
}

function pickPush(prefs) {
  const push = {};
  for (const key of PUSH_FIELDS) {
    if (key in prefs) push[key] = prefs[key];
  }
  return push;
}

function pickMap(prefs) {
  return {
    mapZoomLevels: { ...DEFAULT_MAP_ZOOM_LEVELS, ...(prefs.mapZoomLevels || {}) },
  };
}

function writePartition(name, storage, key, payload) {
  const json = JSON.stringify(payload);
  if (lastSavedJson[name] === json) return;
  safeSet(storage, key, json);
  lastSavedJson[name] = json;
}

function persistSnapshot(prefs, options = {}) {
  const { includeLocation = false, partitions } = options;
  const writeUi = !partitions || partitions.includes('ui');
  const writeMap = !partitions || partitions.includes('map');
  const writePush = !partitions || partitions.includes('push');

  if (writeUi) {
    writePartition('ui', localStorage, STORAGE_KEYS.UI, pickUi(prefs, { includeLocation }));
  }
  if (writeMap) {
    writePartition('map', localStorage, STORAGE_KEYS.MAP, pickMap(prefs));
  }
  if (writePush) {
    writePartition('push', sessionStorage, STORAGE_KEYS.PUSH, pickPush(prefs));
  }
}

function partitionsList(options) {
  return options?.partitions ?? ALL_PARTITIONS;
}

/** Union partitions and OR includeLocation across the debounce window. */
export function mergePersistOptions(prev, next) {
  const mergedParts = new Set([...partitionsList(prev), ...partitionsList(next)]);
  return {
    persist: true,
    partitions: [...mergedParts],
    includeLocation: Boolean(prev?.includeLocation || next?.includeLocation),
  };
}

function migrateLegacyBlob() {
  const raw = safeGet(localStorage, STORAGE_KEYS.LEGACY);
  if (!raw) return;

  const hasNew =
    safeGet(localStorage, STORAGE_KEYS.UI) ||
    safeGet(localStorage, STORAGE_KEYS.MAP) ||
    safeGet(sessionStorage, STORAGE_KEYS.PUSH);
  if (hasNew) {
    safeRemove(localStorage, STORAGE_KEYS.LEGACY);
    return;
  }

  try {
    const parsed = JSON.parse(raw);
    const merged = { ...parsed };
    persistSnapshot(merged, { includeLocation: true, partitions: ALL_PARTITIONS });
    safeRemove(localStorage, STORAGE_KEYS.LEGACY);
  } catch {
    safeRemove(localStorage, STORAGE_KEYS.LEGACY);
  }
}

function readJson(storage, key) {
  const raw = safeGet(storage, key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * @param {object} defaultPrefs
 * @returns {object}
 */
export function loadMergedPrefs(defaultPrefs) {
  migrateLegacyBlob();

  const ui = readJson(localStorage, STORAGE_KEYS.UI) || {};
  const map = readJson(localStorage, STORAGE_KEYS.MAP) || {};
  const push = readJson(sessionStorage, STORAGE_KEYS.PUSH) || {};

  return {
    ...defaultPrefs,
    ...ui,
    ...push,
    mapZoomLevels: {
      ...DEFAULT_MAP_ZOOM_LEVELS,
      ...(map.mapZoomLevels || defaultPrefs.mapZoomLevels || {}),
    },
  };
}

/**
 * @param {object} prefs full merged prefs
 * @param {{ persist?: boolean, includeLocation?: boolean, partitions?: ('ui'|'map'|'push')[] }} options
 */
export function schedulePersistPrefs(prefs, options = {}) {
  if (options.persist === false) return;

  pendingSnapshot = prefs;
  pendingOptions = pendingOptions
    ? mergePersistOptions(pendingOptions, options)
    : { persist: true, ...options };

  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    if (pendingSnapshot) {
      persistSnapshot(pendingSnapshot, pendingOptions || {});
      pendingSnapshot = null;
      pendingOptions = null;
    }
  }, DEBOUNCE_MS);
}

/**
 * @param {object|null} [overridePrefs]
 * @param {{ includeLocation?: boolean, partitions?: ('ui'|'map'|'push')[] }} [overrideOptions]
 */
export function flushPersistPrefs(overridePrefs = null, overrideOptions = null) {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }

  const snapshot = overridePrefs ?? pendingSnapshot;
  let options = pendingOptions || {};
  if (overrideOptions) {
    options = mergePersistOptions(options, overrideOptions);
  }

  if (snapshot) {
    persistSnapshot(snapshot, options);
    pendingSnapshot = null;
    pendingOptions = null;
  }
}

export function disposePersistPrefs() {
  flushPersistPrefs();
}

/** Infer partitions touched by a shallow patch object. */
export function partitionsForPatch(patch) {
  const keys = Object.keys(patch);
  const parts = new Set();
  if (keys.some((k) => PUSH_FIELDS.includes(k))) parts.add('push');
  if (keys.includes('mapZoomLevels')) parts.add('map');
  if (keys.some((k) => !PUSH_FIELDS.includes(k) && k !== 'mapZoomLevels')) parts.add('ui');
  return [...parts];
}

export function patchIncludesLocation(patch) {
  return 'location' in patch || 'locationUpdatedAt' in patch;
}

/** @internal vitest */
export function _resetPersistStateForTests() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = null;
  pendingSnapshot = null;
  pendingOptions = null;
  lastSavedJson.ui = null;
  lastSavedJson.map = null;
  lastSavedJson.push = null;
}
