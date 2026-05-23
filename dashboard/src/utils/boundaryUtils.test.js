import { describe, it, expect } from 'vitest';
import {
  isBoundaryWithHoles,
  getBoundaryOuter,
  getBoundaryHoles,
} from './boundaryUtils.js';

const simple = [[31.0, 34.0], [32.0, 35.0], [31.5, 34.5]];
const outer = [[31.0, 34.0], [32.0, 35.0], [31.5, 34.5], [31.0, 34.0]];
const hole = [[31.2, 34.2], [31.3, 34.3], [31.2, 34.2]];
const withHoles = [outer, hole];

describe('isBoundaryWithHoles', () => {
  it('returns false for a simple polygon ring', () => {
    expect(isBoundaryWithHoles(simple)).toBe(false);
  });

  it('returns true for outer + hole rings', () => {
    expect(isBoundaryWithHoles(withHoles)).toBe(true);
  });

  it('returns false for degenerate two-point "ring"', () => {
    expect(isBoundaryWithHoles([[31.0, 34.0], [32.0, 35.0]])).toBe(false);
  });
});

describe('getBoundaryOuter / getBoundaryHoles', () => {
  it('returns the ring itself for simple polygons', () => {
    expect(getBoundaryOuter(simple)).toBe(simple);
    expect(getBoundaryHoles(simple)).toEqual([]);
  });

  it('splits outer and holes for cutout boundaries', () => {
    expect(getBoundaryOuter(withHoles)).toBe(outer);
    expect(getBoundaryHoles(withHoles)).toEqual([hole]);
  });
});
