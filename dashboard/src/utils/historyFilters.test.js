import { describe, it, expect } from 'vitest';
import {
  canExtendHistoryWindow,
  filterArchiveHistory,
  filterHistoryByOrigin,
  HISTORY_MAX_WINDOW_H,
  HISTORY_PAGE_SIZE,
  HISTORY_WINDOW_STEP_H,
  mergeHistoryById,
  nextHistoryWindowHours,
  resolveHistoryHoursParam,
} from './historyFilters';

const events = [
  { id: '1', trajectories: [{ origin: 'Iran' }] },
  { id: '2', trajectories: [{ origin: 'Lebanon' }] },
  { id: '3', clusters: [{ origin: 'Gaza' }] },
];

describe('filterArchiveHistory', () => {
  it('drops newsFlash rows', () => {
    const rows = [
      { id: '1', category: 'missiles' },
      { id: '2', category: 'newsFlash' },
    ];
    expect(filterArchiveHistory(rows)).toEqual([{ id: '1', category: 'missiles' }]);
  });

  it('returns empty for nullish input', () => {
    expect(filterArchiveHistory(null)).toEqual([]);
  });
});

describe('filterHistoryByOrigin', () => {
  it('returns all when filter is all', () => {
    expect(filterHistoryByOrigin(events, 'all')).toHaveLength(3);
  });

  it('filters by normalized origin', () => {
    expect(filterHistoryByOrigin(events, 'Iran')).toHaveLength(1);
    expect(filterHistoryByOrigin(events, 'Lebanon')).toHaveLength(1);
  });

  it('returns empty for empty input', () => {
    expect(filterHistoryByOrigin(null, 'Iran')).toEqual([]);
  });
});

describe('resolveHistoryHoursParam', () => {
  it('uses rolling window for All Time', () => {
    expect(resolveHistoryHoursParam('all', 24)).toBe('24');
    expect(resolveHistoryHoursParam('all', 48)).toBe('48');
  });

  it('passes fixed timeframe filters through', () => {
    expect(resolveHistoryHoursParam('12')).toBe('12');
    expect(resolveHistoryHoursParam('range:2026-01-01,2026-01-02')).toBe('range:2026-01-01,2026-01-02');
  });
});

describe('history window extend', () => {
  it('steps by 24h until max', () => {
    expect(nextHistoryWindowHours(24)).toBe(48);
    expect(canExtendHistoryWindow('all', 24)).toBe(true);
    expect(canExtendHistoryWindow('all', HISTORY_MAX_WINDOW_H)).toBe(false);
    expect(canExtendHistoryWindow('12', 24)).toBe(false);
  });

  it('defaults page size to 10', () => {
    expect(HISTORY_PAGE_SIZE).toBe(10);
    expect(HISTORY_WINDOW_STEP_H).toBe(24);
  });
});

describe('mergeHistoryById', () => {
  it('skips duplicate ids when appending pages', () => {
    const page1 = [{ id: 'a' }, { id: 'b' }];
    const page2 = [{ id: 'b' }, { id: 'c' }];
    expect(mergeHistoryById(page1, page2)).toEqual([
      { id: 'a' },
      { id: 'b' },
      { id: 'c' },
    ]);
  });

  it('returns incoming when existing is empty', () => {
    expect(mergeHistoryById([], [{ id: '1' }])).toEqual([{ id: '1' }]);
  });
});
