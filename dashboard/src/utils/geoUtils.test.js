import { describe, it, expect } from 'vitest';
import { getConvexHull, getDistance, getCentroid } from './geoUtils.js';

describe('getConvexHull', () => {
  it('should return input unchanged when points is null', () => {
    expect(getConvexHull(null)).toBe(null);
  });

  it('should return input unchanged when fewer than three points', () => {
    const two = [
      [32.0, 34.0],
      [32.1, 34.1],
    ];
    expect(getConvexHull(two)).toEqual(two);
  });

  it('should return hull with at least three vertices for a square', () => {
    const square = [
      [0, 0],
      [0, 1],
      [1, 1],
      [1, 0],
    ];
    const hull = getConvexHull(square);
    expect(hull.length).toBeGreaterThanOrEqual(3);
    expect(hull.length).toBeLessThanOrEqual(4);
  });

  it('should handle collinear points without throwing', () => {
    const line = [
      [32.0, 34.0],
      [32.5, 34.5],
      [33.0, 35.0],
    ];
    const hull = getConvexHull(line);
    expect(Array.isArray(hull)).toBe(true);
    expect(hull.length).toBeGreaterThanOrEqual(2);
  });
});

describe('getDistance', () => {
  it('should return zero for identical points', () => {
    const p = [32.0853, 34.7818];
    expect(getDistance(p, p)).toBe(0);
  });

  it('should return positive distance for different points', () => {
    const telAviv = [32.0853, 34.7818];
    const jerusalem = [31.7683, 35.2137];
    const dist = getDistance(telAviv, jerusalem);
    expect(dist).toBeGreaterThan(50);
    expect(dist).toBeLessThan(60);
  });

  it('should be symmetric between two points', () => {
    const p1 = [32.0, 34.0];
    const p2 = [33.0, 35.0];
    expect(getDistance(p1, p2)).toBeCloseTo(getDistance(p2, p1), 10);
  });
});

describe('getCentroid', () => {
  it('should return null when points is null', () => {
    expect(getCentroid(null)).toBe(null);
  });

  it('should return null when points is empty', () => {
    expect(getCentroid([])).toBe(null);
  });

  it('should return the point when only one coordinate exists', () => {
    expect(getCentroid([[32.0, 34.0]])).toEqual([32.0, 34.0]);
  });

  it('should return arithmetic mean for multiple points', () => {
    expect(
      getCentroid([
        [0, 0],
        [2, 4],
      ])
    ).toEqual([1, 2]);
  });
});
