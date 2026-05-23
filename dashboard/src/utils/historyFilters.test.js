import { describe, it, expect } from 'vitest';
import { filterHistoryByOrigin } from './historyFilters';

const events = [
  { id: '1', trajectories: [{ origin: 'Iran' }] },
  { id: '2', trajectories: [{ origin: 'Lebanon' }] },
  { id: '3', clusters: [{ origin: 'Gaza' }] },
];

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
