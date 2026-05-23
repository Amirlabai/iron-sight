/** Short header pill copy on mobile; full labels on desktop (MOBILE_SHELL_SPEC). */

export function getLiveStatusPillLabel(isConnected, tacticalHealth, { compact = false } = {}) {
  if (!isConnected) {
    return compact ? 'RECONNECTING' : 'RECONNECTING...';
  }
  if (tacticalHealth.status === 'DEGRADED') {
    return compact ? 'DEGRADED' : 'UPLINK DEGRADED';
  }
  if (compact) {
    return 'LIVE';
  }
  return `LIVE INTERCEPT: ${tacticalHealth.source}`;
}

export function getLiveStatusPillAriaLabel(isConnected, tacticalHealth) {
  return getLiveStatusPillLabel(isConnected, tacticalHealth, { compact: false });
}

export function getSandboxStatusPillLabel({ compact = false } = {}) {
  return compact ? 'SANDBOX' : 'TACTICAL SANDBOX ACTIVE';
}
