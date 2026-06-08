import { describe, it, expect } from 'vitest';
import {
  countRenderableCities,
  hydrateEventsForMap,
  shouldSuppressCityDetail,
  CITY_DETAIL_SUPPRESS_THRESHOLD,
  isTimeFrameFilter,
} from './mapRenderBudget';

describe('isTimeFrameFilter', () => {
  it('treats fixed windows as timeframe', () => {
    expect(isTimeFrameFilter('12')).toBe(true);
    expect(isTimeFrameFilter('range:2026-01-01,2026-01-02')).toBe(true);
    expect(isTimeFrameFilter('all')).toBe(false);
  });
});

describe('countRenderableCities', () => {
  it('sums cluster and fallback all_cities', () => {
    const events = [{
      clusters: [{ cities: [{ name: 'A', coords: [1, 2] }, { name: 'B', coords: [3, 4] }] }],
    }];
    expect(countRenderableCities(events)).toBe(2);
  });
});

describe('hydrateEventsForMap', () => {
  it('builds hull from cluster city coords when missing', () => {
    const events = [{
      id: '1',
      clusters: [{
        origin: 'Iran',
        cities: [
          { name: 'A', coords: [32.0, 34.0] },
          { name: 'B', coords: [32.1, 34.5] },
          { name: 'C', coords: [32.2, 34.2] },
        ],
      }],
    }];
    const out = hydrateEventsForMap(events);
    expect(out[0].clusters[0].hull?.length).toBeGreaterThan(2);
    expect(out[0].clusters[0].centroid?.length).toBe(2);
  });
});

describe('shouldSuppressCityDetail', () => {
  it('always suppresses in timeframe mode', () => {
    expect(shouldSuppressCityDetail('timeframe', [{ clusters: [{ cities: [{ coords: [0, 0] }] }] }])).toBe(true);
  });

  it('allows single archive event below cap', () => {
    const cities = Array.from({ length: 100 }, (_, i) => ({ name: `c${i}`, coords: [i, i] }));
    expect(shouldSuppressCityDetail('archive', [{ clusters: [{ cities }] }])).toBe(false);
  });

  it('suppresses multi-event when city stack exceeds multi threshold', () => {
    const batch = (n, start = 0) => Array.from({ length: n }, (_, i) => ({
      name: `c${start + i}`,
      coords: [start + i, start + i],
    }));
    const events = [
      { clusters: [{ cities: batch(41) }] },
      { clusters: [{ cities: batch(40, 100) }] },
    ];
    expect(countRenderableCities(events)).toBe(81);
    expect(shouldSuppressCityDetail('archive', events)).toBe(true);
  });

  it('suppresses at hard cap', () => {
    const cities = Array.from({ length: CITY_DETAIL_SUPPRESS_THRESHOLD }, (_, i) => ({
      name: `c${i}`,
      coords: [i, i],
    }));
    expect(shouldSuppressCityDetail('archive', [{ clusters: [{ cities }] }])).toBe(true);
  });
});
