import { describe, it, expect } from 'vitest';
import {
  formatTime,
  formatDateTime,
  dateToDisplay,
  displayToDate,
  sortEventsByLatestFirst,
  parseEventTimeMs,
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

describe('parseEventTimeMs', () => {
  it('returns 0 for missing or invalid timestamps', () => {
    expect(parseEventTimeMs()).toBe(0);
    expect(parseEventTimeMs('')).toBe(0);
    expect(parseEventTimeMs('not-a-date')).toBe(0);
  });

  it('parses ISO timestamps', () => {
    expect(parseEventTimeMs('2024-03-15T14:30:45')).toBe(
      new Date('2024-03-15T14:30:45').getTime(),
    );
  });
});

describe('sortEventsByLatestFirst', () => {
  it('sorts events newest-first by time', () => {
    const events = [
      { id: 'a', time: '2024-03-15T10:00:00' },
      { id: 'c', time: '2024-03-15T12:00:00' },
      { id: 'b', time: '2024-03-15T11:00:00' },
    ];
    expect(sortEventsByLatestFirst(events).map((e) => e.id)).toEqual(['c', 'b', 'a']);
  });

  it('does not mutate the input array', () => {
    const events = [
      { id: 'old', time: '2024-03-15T10:00:00' },
      { id: 'new', time: '2024-03-15T12:00:00' },
    ];
    sortEventsByLatestFirst(events);
    expect(events[0].id).toBe('old');
  });
});
