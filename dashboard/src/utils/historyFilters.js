import { getEventOrigin } from './mapZoomPresets';

/** Archive / timeframe lists: operational threats only (newsFlash is live-context only). */
export function filterArchiveHistory(events) {
  if (!events?.length) return [];
  return events.filter((ev) => ev.category !== 'newsFlash');
}

/**
 * @param {object[] | null | undefined} events
 * @param {string} originFilter 'all' | country name
 */
export function filterHistoryByOrigin(events, originFilter) {
  if (!events?.length) return [];
  if (!originFilter || originFilter === 'all') return events;
  return events.filter((ev) => getEventOrigin(ev) === originFilter);
}
