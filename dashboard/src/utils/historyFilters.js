import { getEventOrigin } from './mapZoomPresets';

/** Archive / timeframe lists: operational threats only (newsFlash is live-context only). */
export function filterArchiveHistory(events) {
  if (!events?.length) return [];
  return events.filter((ev) => ev.category !== 'newsFlash');
}

/** Append archive pages without duplicate ids (pagination overlap safety). */
export function mergeHistoryById(existing, incoming) {
  if (!incoming?.length) return existing ?? [];
  if (!existing?.length) return [...incoming];
  const seen = new Set(existing.map((ev) => ev.id).filter(Boolean));
  const merged = [...existing];
  for (const ev of incoming) {
    if (ev?.id && seen.has(ev.id)) continue;
    if (ev?.id) seen.add(ev.id);
    merged.push(ev);
  }
  return merged;
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
