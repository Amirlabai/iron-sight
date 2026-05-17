import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

vi.mock('./mapGeometry.js', () => {
  function getEventTargetPoints(event) {
    if (!event) return [];
    const points = [];
    const seen = new Set();
    const add = (coord) => {
      if (!coord || coord.length < 2) return;
      const key = `${coord[0].toFixed(5)},${coord[1].toFixed(5)}`;
      if (seen.has(key)) return;
      seen.add(key);
      points.push([coord[0], coord[1]]);
    };
    for (const cluster of event.clusters || []) {
      if (cluster.hull?.length >= 2) cluster.hull.forEach(add);
      for (const city of cluster.cities || []) add(city.coords);
      add(cluster.centroid);
    }
    for (const c of event.all_cities || []) {
      if (!Array.isArray(c)) add(c.coords);
    }
    return points;
  }
  return { getEventTargetPoints };
});

import { matchesAlertScope, buildAlertNotifyKey } from './alertMatching.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(
  readFileSync(join(__dirname, '../../../shared/alert_matching_vectors.json'), 'utf-8')
);

describe('matchesAlertScope', () => {
  for (const case_ of vectors.matches) {
    it(case_.id, () => {
      const result = matchesAlertScope(case_.user, case_.event, {
        scope: case_.scope,
        radiusKm: case_.radiusKm,
      });
      expect(result).toBe(case_.expect);
    });
  }
});

describe('buildAlertNotifyKey', () => {
  for (const case_ of vectors.notifyKeys) {
    it(case_.id, () => {
      expect(buildAlertNotifyKey(case_.event)).toBe(case_.expect);
    });
  }
});
