const DEFAULT_MAX = 500;

/**
 * Add key to a Set with FIFO eviction when size exceeds maxSize.
 * Re-adding an existing key refreshes its position (LRU-ish via delete + add).
 * @param {Set<string>} set
 * @param {string} key
 * @param {number} [maxSize]
 * @returns {boolean} true if key was newly inserted
 */
export function lruAdd(set, key, maxSize = DEFAULT_MAX) {
  if (set.has(key)) {
    set.delete(key);
    set.add(key);
    return false;
  }
  set.add(key);
  while (set.size > maxSize) {
    const oldest = set.values().next().value;
    set.delete(oldest);
  }
  return true;
}

export function clearLruSet(set) {
  set.clear();
}
