import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

vi.mock('./mapGeometry.js', () => {
  function getEventTargetPoints(event) {
    if (!event) return [];
    const points = [];
    const seen = new Set();
    const add = (coord) => {
      if (!coord || coord.length < 2) return;
      const key = `${coord[0].toFixed(5)},${coord[1].toFixed(5)}`;
      if (seen.has(key)) return;
      seen.add(key);
      points.push([coord[0], coord[1]]);
    };
    for (const cluster of event.clusters || []) {
      if (cluster.hull?.length >= 2) cluster.hull.forEach(add);
      for (const city of cluster.cities || []) {
        if (city && typeof city === 'object') add(city.coords);
      }
      add(cluster.centroid);
    }
    for (const c of event.all_cities || []) {
      if (!Array.isArray(c)) add(c.coords);
    }
    return points;
  }
  return { getEventTargetPoints };
});

vi.mock('./geoUtils.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getDistance: vi.fn(actual.getDistance),
  };
});

import { getDistance } from './geoUtils.js';
import {
  matchesAlertScope,
  filterEventsByScope,
  buildAlertNotifyKey,
  EXACT_MATCH_KM,
  DEFAULT_RADIUS_KM,
} from './alertMatching.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(
  readFileSync(join(__dirname, '../../../shared/alert_matching_vectors.json'), 'utf-8')
);

beforeEach(async () => {
  const m = await vi.importActual('./geoUtils.js');
  vi.mocked(getDistance).mockImplementation(m.getDistance);
});

async function resetGetDistanceToActual() {
  const m = await vi.importActual('./geoUtils.js');
  vi.mocked(getDistance).mockImplementation(m.getDistance);
}

describe('matchesAlertScope', () => {
  describe('shared vector parity', () => {
    for (const case_ of vectors.matches) {
      it(`should return ${case_.expect} when case ${case_.id}`, async () => {
        await resetGetDistanceToActual();
        const result = matchesAlertScope(case_.user, case_.event, {
          scope: case_.scope,
          radiusKm: case_.radiusKm,
        });
        expect(result).toBe(case_.expect);
      });
    }
  });

  it('should return false when event is null', async () => {
    await resetGetDistanceToActual();
    expect(matchesAlertScope([0, 0], null, { scope: 'all' })).toBe(false);
  });

  it('should return false when event is undefined', async () => {
    await resetGetDistanceToActual();
    expect(matchesAlertScope([0, 0], undefined, { scope: 'all' })).toBe(false);
  });

  it('should return false when category is newsFlash regardless of scope', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'n', category: 'newsFlash', all_cities: [] };
    expect(matchesAlertScope([1, 2], ev, { scope: 'all' })).toBe(false);
  });

  it('should return true when scope is all and event is a non-newsflash alert', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'x', category: 'missiles', all_cities: [] };
    expect(matchesAlertScope(null, ev, { scope: 'all' })).toBe(true);
  });

  it('should return false when scope is radius and userLocation has fewer than two elements', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'x', category: 'missiles', clusters: [], all_cities: [] };
    expect(matchesAlertScope([32.0], ev, { scope: 'radius', radiusKm: 10 })).toBe(false);
    expect(matchesAlertScope([], ev, { scope: 'radius', radiusKm: 10 })).toBe(false);
  });

  it('should return false when scope is exact and userLocation is missing', async () => {
    await resetGetDistanceToActual();
    const ev = {
      id: 'x',
      category: 'missiles',
      all_cities: [{ name: 'A', coords: [32.0, 34.0] }],
    };
    expect(matchesAlertScope(null, ev, { scope: 'exact' })).toBe(false);
  });

  it('should return false when scope is unknown string', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'x', category: 'missiles', all_cities: [] };
    expect(matchesAlertScope([32.0, 34.0], ev, { scope: 'invalid' })).toBe(false);
  });

  it('should treat missing prefs.scope as all for matching', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'x', category: 'missiles', all_cities: [] };
    expect(matchesAlertScope([0, 0], ev, {})).toBe(true);
  });

  it('should return false for radius scope when no target points exist', async () => {
    await resetGetDistanceToActual();
    const ev = { id: 'x', category: 'missiles', clusters: [], all_cities: [] };
    expect(matchesAlertScope([32.0, 34.0], ev, { scope: 'radius' })).toBe(false);
  });

  it('should return true for radius scope when distance is within default radius and radiusKm is undefined', async () => {
    const ev = {
      id: 'x',
      category: 'missiles',
      all_cities: [{ coords: [10.0, 20.0] }],
    };
    const user = [10.0, 20.0];
    vi.mocked(getDistance).mockReturnValue(DEFAULT_RADIUS_KM - 1);
    expect(matchesAlertScope(user, ev, { scope: 'radius', radiusKm: undefined })).toBe(true);
    expect(getDistance).toHaveBeenCalled();
  });

  it('should return true for radius scope when any point is within mocked distance', async () => {
    await resetGetDistanceToActual();
    vi.mocked(getDistance).mockImplementation(() => 5);
    const ev = {
      id: 'x',
      category: 'missiles',
      all_cities: [{ coords: [32.0, 34.0] }],
    };
    expect(matchesAlertScope([31.0, 33.0], ev, { scope: 'radius', radiusKm: 10 })).toBe(true);
  });

  it('should return false for radius scope when every point is beyond mocked distance', async () => {
    vi.mocked(getDistance).mockReturnValue(100);
    const ev = {
      id: 'x',
      category: 'missiles',
      all_cities: [{ coords: [32.0, 34.0] }],
    };
    expect(matchesAlertScope([31.0, 33.0], ev, { scope: 'radius', radiusKm: 10 })).toBe(false);
  });

  it('should return true for exact scope when user is inside a cluster hull', async () => {
    await resetGetDistanceToActual();
    const square = [
      [31.9, 33.9],
      [31.9, 34.1],
      [32.1, 34.1],
      [32.1, 33.9],
    ];
    const ev = {
      id: 'x',
      category: 'missiles',
      clusters: [{ hull: square }],
      all_cities: [],
    };
    expect(matchesAlertScope([32.0, 34.0], ev, { scope: 'exact' })).toBe(true);
  });

  it('should return true for exact scope when city distance is within EXACT_MATCH_KM', async () => {
    vi.mocked(getDistance).mockReturnValue(EXACT_MATCH_KM);
    const ev = {
      id: 'x',
      category: 'missiles',
      all_cities: [{ coords: [32.0, 34.0] }],
    };
    expect(matchesAlertScope([32.05, 34.05], ev, { scope: 'exact' })).toBe(true);
  });

  it('should return false for exact scope when outside hull and cities are farther than EXACT_MATCH_KM', async () => {
    vi.mocked(getDistance).mockReturnValue(EXACT_MATCH_KM + 0.1);
    const ev = {
      id: 'x',
      category: 'missiles',
      clusters: [{ hull: [[0, 0], [0, 0.1], [0.1, 0.05]] }],
      all_cities: [{ coords: [50.0, 50.0] }],
    };
    expect(matchesAlertScope([32.0, 34.0], ev, { scope: 'exact' })).toBe(false);
  });

  it('should ignore hulls with fewer than three vertices', async () => {
    vi.mocked(getDistance).mockReturnValue(500);
    const ev = {
      id: 'x',
      category: 'missiles',
      clusters: [{ hull: [[32.0, 34.0], [32.01, 34.0]] }],
      all_cities: [],
    };
    expect(matchesAlertScope([32.0, 34.0], ev, { scope: 'exact' })).toBe(false);
  });
});

describe('filterEventsByScope', () => {
  it('should return empty array when events is null', () => {
    expect(filterEventsByScope(null, [1, 2], { scope: 'radius' })).toEqual([]);
  });

  it('should return empty array when events is undefined', () => {
    expect(filterEventsByScope(undefined, [1, 2], { scope: 'radius' })).toEqual([]);
  });

  it('should return empty array when events is empty', () => {
    expect(filterEventsByScope([], [1, 2], { scope: 'all' })).toEqual([]);
  });

  it('should return all non-newsflash events when prefs is null', () => {
    const evs = [
      { id: '1', category: 'missiles' },
      { id: '2', category: 'newsFlash' },
    ];
    expect(filterEventsByScope(evs, null, null)).toEqual([evs[0]]);
  });

  it('should return all non-newsflash events when scope is all', () => {
    const evs = [
      { id: '1', category: 'missiles' },
      { id: '2', category: 'newsFlash' },
    ];
    expect(filterEventsByScope(evs, [0, 0], { scope: 'all' })).toEqual([evs[0]]);
  });

  it('should filter by matchesAlertScope when scope is not all', async () => {
    await resetGetDistanceToActual();
    const evs = [
      { id: 'a', category: 'missiles', all_cities: [{ coords: [32.0, 34.0] }] },
      { id: 'b', category: 'missiles', all_cities: [{ coords: [40.0, 40.0] }] },
    ];
    vi.mocked(getDistance).mockImplementation((_u, p) => (p[0] >= 39 ? 200 : 2));
    const out = filterEventsByScope(evs, [32.0, 34.0], { scope: 'radius', radiusKm: 100 });
    expect(out.map((e) => e.id)).toEqual(['a']);
  });
});

describe('buildAlertNotifyKey', () => {
  for (const case_ of vectors.notifyKeys) {
    it(`should return expected notify key when case ${case_.id}`, () => {
      expect(buildAlertNotifyKey(case_.event)).toBe(case_.expect);
    });
  }

  it('should return unknown:0 when event is null', () => {
    expect(buildAlertNotifyKey(null)).toBe('unknown:0');
  });

  it('should return unknown:0 when event has no id and no cities', () => {
    expect(buildAlertNotifyKey({})).toBe('unknown:0');
  });

  it('should use zero city count when all_cities is missing', () => {
    expect(buildAlertNotifyKey({ id: 'z' })).toBe('z:0');
  });
});
