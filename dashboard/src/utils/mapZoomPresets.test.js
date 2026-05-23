import { describe, it, expect } from 'vitest';
import { getEventOrigin, resolveMapConfig } from './mapZoomPresets';
import { getZoomLevel, normalizeOriginName } from './mapZoomLevels';
import { calculateBestMapConfig } from './mapGeometry';
import { getDefaultZoom } from './constants';

describe('getEventOrigin', () => {
  it('reads origin from trajectory', () => {
    expect(getEventOrigin({ trajectories: [{ origin: 'Lebanon' }] })).toBe('Lebanon');
  });
});

describe('resolveMapConfig', () => {
  it('uses user origin zoom in automatic framing', () => {
    const events = [
      {
        trajectories: [
          {
            origin: 'Iran',
            origin_coords: [32, 53],
            target_coords: [31.5, 34.5],
          },
        ],
      },
    ];
    const cfg = resolveMapConfig(events, { mapZoomLevels: { 'origin:Iran': 7 } });
    expect(cfg.zoom).toBe(7);
  });

  it('uses user overview zoom for multi-origin', () => {
    const events = [
      {
        trajectories: [
          { origin: 'Iran', origin_coords: [32, 53], target_coords: [31.5, 34.5] },
        ],
      },
      {
        trajectories: [
          { origin: 'Lebanon', origin_coords: [33.5, 35.5], target_coords: [32.5, 35] },
        ],
      },
    ];
    const cfg = resolveMapConfig(events, { mapZoomLevels: { overview: 9 } });
    expect(cfg.zoom).toBe(9);
    expect(cfg.center[0]).toBeCloseTo(31.7683, 2);
  });
});

describe('calculateBestMapConfig with levels', () => {
  it('normalizeOriginName via levels path', () => {
    expect(normalizeOriginName('North Iran')).toBe('Iran');
    expect(getZoomLevel('origin:Iran', { 'origin:Iran': 6 })).toBe(6);
  });

  it('empty events use overview level', () => {
    const cfg = calculateBestMapConfig([], { overview: 10 });
    expect(cfg.zoom).toBe(10);
  });

  it('falls back to default overview', () => {
    const cfg = calculateBestMapConfig([]);
    expect(cfg.zoom).toBe(getDefaultZoom());
  });
});
