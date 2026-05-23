import { describe, it, expect } from 'vitest';
import { isLocationInIsrael } from './israelBounds';

describe('isLocationInIsrael', () => {
  it('returns true for Tel Aviv', () => {
    expect(isLocationInIsrael([32.0853, 34.7818])).toBe(true);
  });

  it('returns true for Jerusalem', () => {
    expect(isLocationInIsrael([31.7683, 35.2137])).toBe(true);
  });

  it('returns false for Amman', () => {
    expect(isLocationInIsrael([31.9454, 35.9284])).toBe(false);
  });

  it('returns false for Cairo', () => {
    expect(isLocationInIsrael([30.0444, 31.2357])).toBe(false);
  });

  it('returns false for invalid point', () => {
    expect(isLocationInIsrael(null)).toBe(false);
    expect(isLocationInIsrael([31])).toBe(false);
  });
});
