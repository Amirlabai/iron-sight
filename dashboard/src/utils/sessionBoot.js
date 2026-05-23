const BOOT_KEY = 'iron-sight-session-booted';

export function hasSessionBooted() {
  try {
    return sessionStorage.getItem(BOOT_KEY) === '1';
  } catch {
    return false;
  }
}

export function markSessionBooted() {
  try {
    sessionStorage.setItem(BOOT_KEY, '1');
  } catch {
    /* ignore */
  }
}
