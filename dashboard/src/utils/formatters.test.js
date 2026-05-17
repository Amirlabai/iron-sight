import { describe, it, expect } from 'vitest';
import {
  formatTime,
  formatDateTime,
  dateToDisplay,
  displayToDate,
} from './formatters.js';

describe('formatTime', () => {
  it('should return empty string when timestamp is empty', () => {
    expect(formatTime('')).toBe('');
    expect(formatTime(null)).toBe('');
  });

  it('should return input unchanged when not a string', () => {
    expect(formatTime(12345)).toBe(12345);
  });

  it('should extract time from ISO T-separated timestamp', () => {
    expect(formatTime('2024-03-15T14:30:45.000Z')).toBe('14:30:45');
  });

  it('should extract time from space-separated timestamp', () => {
    expect(formatTime('2024-03-15 14:30:45')).toBe('14:30:45');
  });

  it('should return input when no T or space separator', () => {
    expect(formatTime('14:30:45')).toBe('14:30:45');
  });
});

describe('formatDateTime', () => {
  it('should return input when timestamp is empty', () => {
    expect(formatDateTime('')).toBe('');
    expect(formatDateTime(null)).toBe(null);
  });

  it('should return input when not a string', () => {
    expect(formatDateTime(42)).toBe(42);
  });

  it('should format ISO timestamp to DD/MM/YYYY HH:MM:SS', () => {
    expect(formatDateTime('2024-03-15T14:30:45.000Z')).toBe('15/03/2024 14:30:45');
  });

  it('should format space-separated timestamp', () => {
    expect(formatDateTime('2024-03-15 14:30:45')).toBe('15/03/2024 14:30:45');
  });

  it('should return input when date part is malformed', () => {
    expect(formatDateTime('bad-timestamp')).toBe('bad-timestamp');
  });

  it('should return input when only one part exists', () => {
    expect(formatDateTime('2024-03-15')).toBe('2024-03-15');
  });
});

describe('dateToDisplay', () => {
  it('should return empty string when input is empty', () => {
    expect(dateToDisplay('')).toBe('');
    expect(dateToDisplay(null)).toBe('');
  });

  it('should convert YYYY-MM-DD to DD/MM/YYYY', () => {
    expect(dateToDisplay('2024-03-15')).toBe('15/03/2024');
  });

  it('should return input when format is invalid', () => {
    expect(dateToDisplay('2024')).toBe('2024');
  });
});

describe('displayToDate', () => {
  it('should return empty string when input is empty', () => {
    expect(displayToDate('')).toBe('');
    expect(displayToDate(null)).toBe('');
  });

  it('should convert DD/MM/YYYY to YYYY-MM-DD', () => {
    expect(displayToDate('15/03/2024')).toBe('2024-03-15');
  });

  it('should round-trip with dateToDisplay', () => {
    const iso = '2024-06-01';
    expect(displayToDate(dateToDisplay(iso))).toBe(iso);
  });

  it('should return input when format is invalid', () => {
    expect(displayToDate('2024-03-15')).toBe('2024-03-15');
  });
});
