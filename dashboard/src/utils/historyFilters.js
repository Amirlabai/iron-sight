import { getEventOrigin } from './mapZoomPresets';

/**
 * @param {object[] | null | undefined} events
 * @param {string} originFilter 'all' | country name
 */
export function filterHistoryByOrigin(events, originFilter) {
  if (!events?.length) return [];
  if (!originFilter || originFilter === 'all') return events;
  return events.filter((ev) => getEventOrigin(ev) === originFilter);
}
