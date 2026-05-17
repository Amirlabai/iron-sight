import { describe, it, expect } from 'vitest';
import { categoryTint, getDefaultZoom } from './constants.js';

describe('getDefaultZoom', () => {
  it('should return numeric zoom level', () => {
    expect(getDefaultZoom()).toBe(8);
  });
});

describe('categoryTint', () => {
  it('should return color-mix CSS with default percent', () => {
    expect(categoryTint('#ff4d4d')).toBe(
      'color-mix(in srgb, #ff4d4d 8%, transparent)'
    );
  });

  it('should use custom percent when provided', () => {
    expect(categoryTint('#4d94ff', 20)).toBe(
      'color-mix(in srgb, #4d94ff 20%, transparent)'
    );
  });
});
