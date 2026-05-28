import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  STORAGE_KEYS,
  loadMergedPrefs,
  schedulePersistPrefs,
  flushPersistPrefs,
  mergePersistOptions,
  partitionsForPatch,
  _resetPersistStateForTests,
} from './alertPrefsStorage';

function createMemoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => {
      map.set(key, String(value));
    },
    removeItem: (key) => {
      map.delete(key);
    },
    clear: () => map.clear(),
    _map: map,
  };
}

describe('mergePersistOptions', () => {
  it('unions partitions across calls', () => {
    const merged = mergePersistOptions(
      { partitions: ['ui'], includeLocation: false },
      { partitions: ['push'], includeLocation: false },
    );
    expect(merged.partitions.sort()).toEqual(['push', 'ui']);
    expect(merged.includeLocation).toBe(false);
  });

  it('ORs includeLocation when any call requests it', () => {
    const merged = mergePersistOptions(
      { partitions: ['ui'], includeLocation: false },
      { partitions: ['push'], includeLocation: true },
    );
    expect(merged.includeLocation).toBe(true);
  });
});

describe('partitionsForPatch', () => {
  it('routes push and ui keys separately', () => {
    expect(partitionsForPatch({ scope: 'radius' }).sort()).toEqual(['ui']);
    expect(partitionsForPatch({ pushEndpoint: 'x' }).sort()).toEqual(['push']);
    expect(
      partitionsForPatch({ scope: 'all', pushEndpoint: 'x', mapZoomLevels: {} }).sort(),
    ).toEqual(['map', 'push', 'ui']);
  });
});

describe('alertPrefsStorage persist', () => {
  let local;
  let session;

  beforeEach(() => {
    vi.useFakeTimers();
    _resetPersistStateForTests();
    local = createMemoryStorage();
    session = createMemoryStorage();
    vi.stubGlobal('localStorage', local);
    vi.stubGlobal('sessionStorage', session);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    _resetPersistStateForTests();
  });

  const basePrefs = {
    complete: true,
    notifyPermission: 'granted',
    geoPermission: 'granted',
    scope: 'radius',
    radiusKm: 10,
    wizardDismissed: true,
    showUserLocationOnMap: true,
    location: [32.1, 34.8],
    locationUpdatedAt: '2026-01-01T00:00:00.000Z',
    pushEndpoint: 'https://push.example/ep',
    pushClientToken: 'tok',
    mapZoomLevels: { missiles: 8 },
  };

  it('migrates legacy iron_sight_alert_prefs into split keys', () => {
    local.setItem(
      STORAGE_KEYS.LEGACY,
      JSON.stringify({
        scope: 'exact',
        pushEndpoint: 'https://legacy/ep',
        pushClientToken: 'legacy-tok',
        mapZoomLevels: { missiles: 9 },
      }),
    );

    const loaded = loadMergedPrefs({
      scope: 'all',
      pushEndpoint: null,
      pushClientToken: null,
      mapZoomLevels: { missiles: 6 },
    });

    expect(local.getItem(STORAGE_KEYS.LEGACY)).toBeNull();
    expect(loaded.scope).toBe('exact');
    expect(loaded.pushEndpoint).toBe('https://legacy/ep');
    expect(session.getItem(STORAGE_KEYS.PUSH)).toContain('legacy-tok');
    expect(loaded.mapZoomLevels.missiles).toBe(9);
  });

  it('coalesces ui then push partitions within debounce window', () => {
    schedulePersistPrefs(
      { ...basePrefs, scope: 'all', pushEndpoint: null, pushClientToken: null },
      { partitions: ['ui'], includeLocation: false },
    );
    schedulePersistPrefs(
      { ...basePrefs, scope: 'all' },
      { partitions: ['push'], includeLocation: false },
    );

    vi.advanceTimersByTime(300);

    const ui = JSON.parse(local.getItem(STORAGE_KEYS.UI));
    const push = JSON.parse(session.getItem(STORAGE_KEYS.PUSH));

    expect(ui.scope).toBe('all');
    expect(ui.location).toBeUndefined();
    expect(push.pushEndpoint).toBe('https://push.example/ep');
  });

  it('skip-if-unchanged avoids duplicate localStorage writes', () => {
    schedulePersistPrefs(basePrefs, { partitions: ['ui'], includeLocation: false });
    vi.advanceTimersByTime(300);
    const writesAfterFirst = local._map.size;

    schedulePersistPrefs(basePrefs, { partitions: ['ui'], includeLocation: false });
    vi.advanceTimersByTime(300);
    expect(local._map.size).toBe(writesAfterFirst);
  });

  it('flushPersistPrefs writes immediately with merged pending options', () => {
    schedulePersistPrefs(basePrefs, { partitions: ['map'] });
    flushPersistPrefs();

    expect(local.getItem(STORAGE_KEYS.MAP)).toContain('missiles');
    expect(session.getItem(STORAGE_KEYS.PUSH)).toBeNull();
  });

  it('flushPersistPrefs override can persist location into ui partition', () => {
    flushPersistPrefs(basePrefs, { partitions: ['ui'], includeLocation: true });

    const ui = JSON.parse(local.getItem(STORAGE_KEYS.UI));
    expect(ui.location).toEqual([32.1, 34.8]);
    expect(ui.locationUpdatedAt).toBe('2026-01-01T00:00:00.000Z');
  });

  it('loadMergedPrefs restores location when present in ui storage', () => {
    local.setItem(
      STORAGE_KEYS.UI,
      JSON.stringify({
        scope: 'radius',
        geoPermission: 'granted',
        location: [31.5, 34.9],
        locationUpdatedAt: '2026-05-01T12:00:00.000Z',
      }),
    );

    const loaded = loadMergedPrefs({ scope: 'all', location: null, geoPermission: 'denied' });
    expect(loaded.location).toEqual([31.5, 34.9]);
    expect(loaded.geoPermission).toBe('granted');
  });
});
