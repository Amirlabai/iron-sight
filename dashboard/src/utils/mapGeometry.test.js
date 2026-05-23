import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  boundsKey,
  resolveOriginPinCoords,
  getEventTargetPoints,
  calculateBestMapConfig,
  calculateArchiveMapConfig,
  calculateTimeframeMapConfig,
  getFitPadding,
} from './mapGeometry.js';
import {
  ISRAEL_CENTER,
  MOBILE_LAYOUT_BREAKPOINT,
  TACTICAL_BOUNDARIES,
  isBoundaryWithHoles,
  flattenBoundary,
} from './constants.js';
import { squareHull, missileEventNear, missileEventWithHull } from '../test-utils/fixtures/events.js';

describe('boundsKey', () => {
  it('should return empty string when bounds is null', () => {
    expect(boundsKey(null)).toBe('');
  });

  it('should return empty string when bounds is empty', () => {
    expect(boundsKey([])).toBe('');
  });

  it('should encode length and first/last coordinates', () => {
    const bounds = [
      [31.0, 34.0],
      [32.0, 35.0],
    ];
    expect(boundsKey(bounds)).toBe('2:31,34:32,35');
  });
});

describe('resolveOriginPinCoords', () => {
  it('should prefer marker_coords from trajectory', () => {
    const traj = { marker_coords: [33.0, 35.0], origin_coords: [30.0, 30.0] };
    expect(resolveOriginPinCoords('Iran', traj)).toEqual([33.0, 35.0]);
  });

  it('should use tactical boundary centroid when origin is known', () => {
    const coords = resolveOriginPinCoords('Iran', null);
    expect(Array.isArray(coords)).toBe(true);
    expect(coords.length).toBe(2);
  });

  it('should fall back to origin_coords when boundary missing', () => {
    const traj = { origin_coords: [29.0, 34.0] };
    expect(resolveOriginPinCoords('UnknownOrigin', traj)).toEqual([29.0, 34.0]);
  });

  it('should return null when no coords available', () => {
    expect(resolveOriginPinCoords('UnknownOrigin', null)).toBe(null);
  });
});

describe('getEventTargetPoints', () => {
  it('should return empty array when event is null', () => {
    expect(getEventTargetPoints(null)).toEqual([]);
  });

  it('should collect all_cities coords', () => {
    const pts = getEventTargetPoints(missileEventNear);
    expect(pts).toEqual([[32.0853, 34.7818]]);
  });

  it('should collect hull vertices from clusters', () => {
    const pts = getEventTargetPoints(missileEventWithHull);
    for (const v of squareHull) {
      expect(pts.some((p) => p[0] === v[0] && p[1] === v[1])).toBe(true);
    }
  });

  it('should deduplicate coords at five decimal places', () => {
    const event = {
      all_cities: [
        { coords: [32.085312, 34.781812] },
        { coords: [32.085314, 34.781814] },
      ],
    };
    expect(getEventTargetPoints(event).length).toBe(1);
  });
});

describe('calculateBestMapConfig', () => {
  it('should return Israel center when events is empty', () => {
    const cfg = calculateBestMapConfig([]);
    expect(cfg.center).toEqual(ISRAEL_CENTER);
    expect(cfg.bounds).toBe(null);
  });

  it('should return Israel center when events is null', () => {
    const cfg = calculateBestMapConfig(null);
    expect(cfg.center).toEqual(ISRAEL_CENTER);
  });

  it('should use event center when no trajectories exist', () => {
    const cfg = calculateBestMapConfig([
      { center: [32.5, 34.5], zoom_level: 9 },
    ]);
    expect(cfg.center).toEqual([32.5, 34.5]);
    expect(cfg.zoom).toBe(9);
  });
});

describe('calculateArchiveMapConfig', () => {
  it('should fit bounds when multiple points exist', () => {
    const event = {
      all_cities: [
        { coords: [32.0, 34.0] },
        { coords: [33.0, 35.0] },
      ],
    };
    const cfg = calculateArchiveMapConfig(event);
    expect(cfg.bounds).toHaveLength(2);
    expect(cfg.center[0]).toBeCloseTo(32.5, 5);
  });

  it('should center on single point with zoom 10', () => {
    const cfg = calculateArchiveMapConfig(missileEventNear);
    expect(cfg.center).toEqual([32.0853, 34.7818]);
    expect(cfg.zoom).toBe(10);
    expect(cfg.bounds).toBe(null);
  });
});

describe('calculateTimeframeMapConfig', () => {
  it('should return Israel overview config', () => {
    const cfg = calculateTimeframeMapConfig();
    expect(cfg.center).toEqual(ISRAEL_CENTER);
    expect(cfg.zoom).toBeGreaterThan(0);
  });

  it('should flatten Israel cutout boundary for fit bounds', () => {
    const israel = TACTICAL_BOUNDARIES['Israel'];
    expect(isBoundaryWithHoles(israel)).toBe(true);
    const cfg = calculateTimeframeMapConfig();
    expect(cfg.bounds).not.toBeNull();
    expect(cfg.bounds.length).toBeGreaterThan(100);
    expect(Array.isArray(cfg.bounds[0])).toBe(true);
    expect(typeof cfg.bounds[0][0]).toBe('number');
    expect(cfg.bounds).toEqual(flattenBoundary(israel));
  });
});

describe('getFitPadding', () => {
  const originalInnerWidth = globalThis.window?.innerWidth;

  afterEach(() => {
    if (originalInnerWidth !== undefined) {
      vi.stubGlobal('window', { innerWidth: originalInnerWidth });
    }
  });

  it('should use larger bottom padding on mobile viewport', () => {
    vi.stubGlobal('window', { innerWidth: MOBILE_LAYOUT_BREAKPOINT });
    const pad = getFitPadding();
    expect(pad.paddingBottomRight[1]).toBe(200);
  });

  it('should use standard bottom padding on desktop viewport', () => {
    vi.stubGlobal('window', { innerWidth: MOBILE_LAYOUT_BREAKPOINT + 1 });
    const pad = getFitPadding();
    expect(pad.paddingBottomRight[1]).toBe(40);
  });
});
