/**
 * Session debug logger (dev only). Foldable via #region agent log at call sites.
 * Stripped from production behavior: all exports no-op when import.meta.env.DEV is false.
 */
const ENDPOINT = 'http://127.0.0.1:7807/ingest/0e6084b2-dc50-4393-ac44-ad43637ef8c9';
const SESSION_ID = '099dfa';

export const AGENT_DEBUG_ENABLED = import.meta.env.DEV;

/** Burst: websocket onmessage — live path is ~1 multi_alert/s; threshold flags reconnect/flood (>20/s). */
export const WS_MESSAGE_BURST = { threshold: 20, windowMs: 1000 };

/** Burst: map invalidateSize — mobile chrome can fire several resizes in ~1s; avoid session false-positives. */
export const MAP_RESIZE_BURST = { threshold: 12, windowMs: 800 };

const throttleLast = typeof window !== 'undefined' ? {} : null;

function isEnabled() {
  return AGENT_DEBUG_ENABLED && typeof window !== 'undefined';
}

export function agentDebugLog(location, message, data, hypothesisId, runId = 'pre-fix') {
  if (!isEnabled()) return;
  const entry = {
    sessionId: SESSION_ID,
    location,
    message,
    data,
    hypothesisId,
    runId,
    timestamp: Date.now(),
  };
  if (!window.__AGENT_DEBUG__) {
    window.__AGENT_DEBUG__ = [];
  }
  const buf = window.__AGENT_DEBUG__;
  buf.push(entry);
  if (buf.length > 50) {
    buf.splice(0, buf.length - 50);
  }
  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': SESSION_ID },
    body: JSON.stringify(entry),
  }).catch(() => {});
}

/** At most one log per key per intervalMs (longtask observer, etc.). */
export function agentDebugLogThrottled(key, intervalMs, location, message, data, hypothesisId) {
  if (!isEnabled()) return;
  const now = Date.now();
  const last = throttleLast[key] ?? 0;
  if (now - last < intervalMs) return;
  throttleLast[key] = now;
  agentDebugLog(location, message, data, hypothesisId);
}

/** Log once when call count in windowMs reaches threshold (burst detector). */
export function agentDebugBurst(
  key,
  location,
  message,
  data,
  hypothesisId,
  threshold = 8,
  windowMs = 500,
) {
  if (!isEnabled()) return;
  const store = window.__AGENT_BURST__ || (window.__AGENT_BURST__ = {});
  const now = Date.now();
  const bucket = (store[key] || []).filter((t) => now - t < windowMs);
  bucket.push(now);
  store[key] = bucket;
  if (bucket.length === threshold) {
    agentDebugLog(location, message, { ...data, count: bucket.length, windowMs }, hypothesisId);
    store[key] = [];
  }
}
