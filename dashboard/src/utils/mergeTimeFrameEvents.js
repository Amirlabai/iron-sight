import { getConvexHull, getCentroid, getDistance } from './geoUtils';

/** Proximity threshold (km) for merging clusters in timeframe view. */
export const CLUSTER_MERGE_DISTANCE_KM = 8;

function copyEventBase(source) {
  return {
    title: source.title,
    time: source.time,
    visual_config: source.visual_config,
    verified: source.verified,
    manual_origin: source.manual_origin,
    is_simulation: source.is_simulation,
    center: source.center,
    zoom_level: source.zoom_level,
    highlight_origins: source.highlight_origins,
  };
}

function clusterCityNames(cluster) {
  return new Set(
    (cluster.cities ?? []).map((c) => (typeof c === 'string' ? c : c.name)),
  );
}

function clustersShareCity(c1, c2) {
  if (!c1.cities || !c2.cities) return false;
  const names1 = clusterCityNames(c1);
  for (const name of clusterCityNames(c2)) {
    if (names1.has(name)) return true;
  }
  return false;
}

function shouldMergeClusters(c1, c2, mergeDistanceKm) {
  if (c1.centroid && c2.centroid) {
    if (getDistance(c1.centroid, c2.centroid) < mergeDistanceKm) return true;
  }
  return clustersShareCity(c1, c2);
}

function groupClustersByProximity(allClusters, mergeDistanceKm) {
  const superClusters = [];
  const visited = new Set();

  for (let i = 0; i < allClusters.length; i += 1) {
    if (visited.has(i)) continue;

    const currentGroup = [];
    const queue = [i];
    visited.add(i);

    while (queue.length > 0) {
      const idx = queue.shift();
      const c1 = allClusters[idx];
      currentGroup.push(c1);

      for (let j = 0; j < allClusters.length; j += 1) {
        if (visited.has(j)) continue;
        const c2 = allClusters[j];
        if (shouldMergeClusters(c1, c2, mergeDistanceKm)) {
          visited.add(j);
          queue.push(j);
        }
      }
    }
    superClusters.push(currentGroup);
  }

  return superClusters;
}

function buildSuperEvent(group, events, category, origin, key, sIdx) {
  const baseEvent = copyEventBase(events[0]);

  const times = group.map((c) => new Date(c.time || baseEvent.time).getTime());
  const minTime = new Date(Math.min(...times));
  const maxTime = new Date(Math.max(...times));
  const timeRangeStr = `${minTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${maxTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  const superEvent = {
    ...baseEvent,
    id: `merged_${key}_${sIdx}`,
    category,
    mergedCount: group.length,
    timeRange: timeRangeStr,
    all_cities: [],
    clusters: [{
      origin,
      cities: [],
      hull: [],
      centroid: null,
    }],
  };

  const masterCluster = superEvent.clusters[0];
  const points = [];
  const cityNames = new Set();

  group.forEach((c) => {
    if (c.cities) {
      c.cities.forEach((city) => {
        const name = typeof city === 'string' ? city : city.name;
        if (!cityNames.has(name)) {
          masterCluster.cities.push(city);
          superEvent.all_cities.push(city);
          cityNames.add(name);
        }
        if (city.coords) points.push(city.coords);
      });
    }
    if (c.hull) points.push(...c.hull);
    if (c.centroid) points.push(c.centroid);
  });

  if (points.length > 0) {
    masterCluster.hull = getConvexHull(points);
    masterCluster.centroid = getCentroid(points);
  }

  const trajSample = events
    .flatMap((e) => e.trajectories || [])
    .find((t) => t.origin === origin);
  if (trajSample) {
    superEvent.trajectories = [trajSample];
  } else {
    const memberEntries = events
      .flatMap((e) => e.trajectories || [])
      .filter((t) => t.origin === origin && t.origin_coords?.length >= 2);
    if (memberEntries.length > 0) {
      const avgLat = memberEntries.reduce((s, t) => s + t.origin_coords[0], 0) / memberEntries.length;
      const avgLng = memberEntries.reduce((s, t) => s + t.origin_coords[1], 0) / memberEntries.length;
      const avg = [avgLat, avgLng];
      superEvent.trajectories = [{
        origin,
        origin_coords: avg,
        marker_coords: avg,
      }];
    }
  }

  return superEvent;
}

/**
 * Merge timeframe history events by category + origin, clustering nearby footprints.
 * @param {object[]} filteredHistory
 * @param {{ mergeDistanceKm?: number }} [options]
 */
export function mergeTimeFrameEvents(filteredHistory, options = {}) {
  const mergeDistanceKm = options.mergeDistanceKm ?? CLUSTER_MERGE_DISTANCE_KM;
  const eventGroups = {};

  filteredHistory.forEach((ev) => {
    const category = ev.category || 'missiles';
    const origin = ev.trajectories?.[0]?.origin || ev.clusters?.[0]?.origin || 'unknown';
    const key = `${category}_${origin}`;
    if (!eventGroups[key]) eventGroups[key] = [];
    eventGroups[key].push(ev);
  });

  const mergedEvents = [];

  Object.entries(eventGroups).forEach(([key, events]) => {
    const sep = key.indexOf('_');
    const category = key.slice(0, sep);
    const origin = key.slice(sep + 1);

    const allClusters = [];
    events.forEach((ev) => {
      if (ev.clusters) allClusters.push(...ev.clusters);
    });

    if (allClusters.length === 0) return;

    const superClusters = groupClustersByProximity(allClusters, mergeDistanceKm);

    superClusters.forEach((group, sIdx) => {
      mergedEvents.push(buildSuperEvent(group, events, category, origin, key, sIdx));
    });
  });

  return mergedEvents;
}
