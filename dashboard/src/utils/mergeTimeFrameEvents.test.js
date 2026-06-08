import { describe, it, expect } from 'vitest';
import {
  mergeTimeFrameEvents,
  CLUSTER_MERGE_DISTANCE_KM,
} from './mergeTimeFrameEvents.js';

describe('mergeTimeFrameEvents', () => {
  it('exports CLUSTER_MERGE_DISTANCE_KM as 8', () => {
    expect(CLUSTER_MERGE_DISTANCE_KM).toBe(8);
  });

  it('returns empty array for empty history', () => {
    expect(mergeTimeFrameEvents([])).toEqual([]);
  });

  it('merges events with same category and origin', () => {
    const history = [
      {
        id: 'a',
        category: 'missiles',
        time: '2024-01-01T10:00:00Z',
        title: 'Alert A',
        clusters: [{
          origin: 'Iran',
          centroid: [32.0, 34.0],
          cities: [{ name: 'Tel Aviv', coords: [32.0, 34.0] }],
        }],
        trajectories: [{ origin: 'Iran', origin_coords: [33.0, 44.0] }],
      },
      {
        id: 'b',
        category: 'missiles',
        time: '2024-01-01T10:05:00Z',
        title: 'Alert B',
        clusters: [{
          origin: 'Iran',
          centroid: [32.01, 34.01],
          cities: [{ name: 'Ramat Gan', coords: [32.01, 34.01] }],
        }],
        trajectories: [{ origin: 'Iran', origin_coords: [33.0, 44.0] }],
      },
    ];

    const merged = mergeTimeFrameEvents(history);
    expect(merged).toHaveLength(1);
    expect(merged[0].mergedCount).toBe(2);
    expect(merged[0].id).toMatch(/^merged_missiles_Iran_0$/);
    expect(merged[0].all_cities).toHaveLength(2);
    expect(merged[0].title).toBe('Alert A');
  });

  it('keeps separate groups for different origins', () => {
    const history = [
      {
        id: 'a',
        category: 'missiles',
        clusters: [{ origin: 'Iran', centroid: [32.0, 34.0], cities: [] }],
        trajectories: [{ origin: 'Iran' }],
      },
      {
        id: 'b',
        category: 'missiles',
        clusters: [{ origin: 'Lebanon', centroid: [33.0, 35.0], cities: [] }],
        trajectories: [{ origin: 'Lebanon' }],
      },
    ];

    const merged = mergeTimeFrameEvents(history);
    expect(merged).toHaveLength(2);
  });

  it('merges clusters sharing a city name even when far apart', () => {
    const history = [{
      id: 'a',
      category: 'missiles',
      time: '2024-01-01T10:00:00Z',
      clusters: [
        {
          origin: 'Iran',
          centroid: [32.0, 34.0],
          cities: [{ name: 'Shared City', coords: [32.0, 34.0] }],
        },
        {
          origin: 'Iran',
          centroid: [35.0, 36.0],
          cities: [{ name: 'Shared City', coords: [35.0, 36.0] }],
        },
      ],
      trajectories: [{ origin: 'Iran' }],
    }];

    const merged = mergeTimeFrameEvents(history);
    expect(merged).toHaveLength(1);
    expect(merged[0].mergedCount).toBe(2);
  });
});
