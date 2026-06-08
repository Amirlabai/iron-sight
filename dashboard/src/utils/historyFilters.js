import { getEventOrigin } from './mapZoomPresets';

/** Rows per archive page fetch (slim list view). */
export const HISTORY_PAGE_SIZE = 10;
/** All-time browse: start at last N hours, extend by this step on SHOW MORE. */
export const HISTORY_WINDOW_STEP_H = 24;
/** Cap auto-extend for All Time (90 days). */
export const HISTORY_MAX_WINDOW_H = HISTORY_WINDOW_STEP_H * 90;
/** Page size when pulling a full timeframe window (list view). */
export const TIMEFRAME_FETCH_PAGE_SIZE = 100;
/** Safety cap on events loaded for one timeframe query. */
export const TIMEFRAME_FETCH_MAX_EVENTS = 5000;

/** Map UI time filter to API hours query (All Time uses rolling window, not unbounded). */
export function resolveHistoryHoursParam(timeFrame, windowHours = HISTORY_WINDOW_STEP_H) {
  if (timeFrame === 'all') return String(windowHours);
  if (timeFrame.startsWith('range:')) return timeFrame;
  return timeFrame;
}

export function canExtendHistoryWindow(timeFrame, windowHours) {
  return timeFrame === 'all' && windowHours < HISTORY_MAX_WINDOW_H;
}

export function nextHistoryWindowHours(windowHours) {
  return Math.min(windowHours + HISTORY_WINDOW_STEP_H, HISTORY_MAX_WINDOW_H);
}

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
