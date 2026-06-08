import { describe, it, expect } from 'vitest';
import { parseSandboxCities } from './parseSandboxCities.js';

describe('parseSandboxCities', () => {
  it('returns empty array for blank input', () => {
    expect(parseSandboxCities('')).toEqual([]);
    expect(parseSandboxCities('   ')).toEqual([]);
    expect(parseSandboxCities(null)).toEqual([]);
  });

  it('splits on semicolons', () => {
    expect(parseSandboxCities('Tel Aviv; Haifa; Jerusalem')).toEqual([
      'Tel Aviv',
      'Haifa',
      'Jerusalem',
    ]);
  });

  it('splits on newlines', () => {
    expect(parseSandboxCities('Tel Aviv\nHaifa')).toEqual(['Tel Aviv', 'Haifa']);
  });

  it('trims whitespace and drops empty segments', () => {
    expect(parseSandboxCities(' Tel Aviv ; ; Haifa ')).toEqual(['Tel Aviv', 'Haifa']);
  });
});
