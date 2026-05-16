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
