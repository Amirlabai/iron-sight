import { describe, it, expect } from 'vitest';
import { filterArchiveHistory, filterHistoryByOrigin, mergeHistoryById } from './historyFilters';

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
