import { STRATEGIC_METADATA } from './constants';

const INTERNAL_ORIGINS = new Set(['hostileAircraftIntrusion']);

export const ORIGIN_FILTER_OPTIONS = Object.keys(STRATEGIC_METADATA)
  .filter((name) => !INTERNAL_ORIGINS.has(name))
  .sort();

export function normalizeOriginName(origin) {
  if (!origin) return null;
  if (origin === 'North Iran') return 'Iran';
  return origin;
}

/** Prefer operator label, then stored trajectory / cluster origin. */
export function getEventOrigin(event) {
  const raw =
    event?.manual_origin
    || event?.trajectories?.[0]?.origin
    || event?.clusters?.[0]?.origin;
  return normalizeOriginName(raw);
}

export function filterHistoryByOrigin(events, originFilter) {
  if (!events?.length) return [];
  if (!originFilter || originFilter === 'all') return events;
  const target = normalizeOriginName(originFilter) || originFilter;
  return events.filter((ev) => getEventOrigin(ev) === target);
}
