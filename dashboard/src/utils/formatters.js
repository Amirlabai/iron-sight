/**
 * Formats a timestamp string (ISO or space-separated) to HH:MM:SS.
 * @param {string} ts - The timestamp string.
 * @returns {string} - The formatted time string.
 */
export const formatTime = (ts) => {
  if (!ts) return '';
  if (typeof ts !== 'string') return ts;
  if (ts.includes('T')) return ts.split('T')[1].substring(0, 8);
  if (ts.includes(' ')) return ts.split(' ')[1].substring(0, 8);
  return ts;
};

/**
 * Formats a timestamp string to DD/MM/YYYY HH:MM:SS.
 * @param {string} ts - The timestamp string.
 * @returns {string} - The formatted datetime string.
 */
export const formatDateTime = (ts) => {
  if (!ts || typeof ts !== 'string') return ts;
  const parts = ts.includes('T') ? ts.split('T') : ts.split(' ');
  if (parts.length < 2) return ts;
  const [date, time] = parts;
  const dateParts = date.split('-');
  if (dateParts.length !== 3) return ts;
  const [y, m, d] = dateParts;
  return `${d}/${m}/${y} ${time.substring(0, 8)}`;
};

/**
 * Converts YYYY-MM-DD to DD/MM/YYYY.
 */
export const dateToDisplay = (dateStr) => {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
};

/**
 * Converts DD/MM/YYYY to YYYY-MM-DD.
 */
export const displayToDate = (displayStr) => {
  if (!displayStr) return '';
  const parts = displayStr.split('/');
  if (parts.length !== 3) return displayStr;
  return `${parts[2]}-${parts[1]}-${parts[0]}`;
};

/**
 * Parses an event timestamp to epoch ms; returns 0 when missing or invalid.
 */
export const parseEventTimeMs = (ts) => {
  if (!ts) return 0;
  const ms = new Date(ts).getTime();
  return Number.isFinite(ms) ? ms : 0;
};

/**
 * Returns a copy of events sorted newest-first by `time`.
 */
export const sortEventsByLatestFirst = (events) => {
  if (!events?.length) return events || [];
  return [...events].sort(
    (a, b) => parseEventTimeMs(b.time) - parseEventTimeMs(a.time),
  );
};
