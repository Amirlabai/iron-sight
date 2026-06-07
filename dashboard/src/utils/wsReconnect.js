export const WS_RECONNECT_BASE_MS = 3000;
export const WS_RECONNECT_MAX_MS = 60_000;
/** First N reconnect waits stay at base delay before exponential backoff. */
export const WS_RECONNECT_FLAT_ATTEMPTS = 3;

/** Backoff: 3s × 3 attempts, then 6s, 12s, 24s, … capped at 60s. */
export function getWsReconnectDelayMs(failCount) {
  const n = Math.max(0, failCount);
  if (n < WS_RECONNECT_FLAT_ATTEMPTS) {
    return WS_RECONNECT_BASE_MS;
  }
  const doubled = WS_RECONNECT_BASE_MS * 2;
  const exponent = n - WS_RECONNECT_FLAT_ATTEMPTS;
  return Math.min(doubled * 2 ** exponent, WS_RECONNECT_MAX_MS);
}

/** Survives React StrictMode remounts so backoff is not reset every 3s. */
let failStreak = 0;

export function consumeWsReconnectDelayMs() {
  const delay = getWsReconnectDelayMs(failStreak);
  failStreak += 1;
  return delay;
}

export function resetWsFailStreak() {
  failStreak = 0;
}

/** @internal tests only */
export function _getWsFailStreakForTests() {
  return failStreak;
}

/** @internal tests only */
export function _setWsFailStreakForTests(n) {
  failStreak = Math.max(0, n);
}
