import { useCallback, useState } from 'react';

const STORAGE_KEY = 'iron-sight-cookie-consent';

/** @returns {'accepted' | 'essential' | null} */
function readStored() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === 'accepted' || value === 'essential') return value;
    return null;
  } catch {
    return null;
  }
}

export function useCookieConsent() {
  const [consent, setConsent] = useState(readStored);

  const accept = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, 'accepted');
    } catch {
      /* ignore */
    }
    setConsent('accepted');
  }, []);

  const dismissEssential = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, 'essential');
    } catch {
      /* ignore */
    }
    setConsent('essential');
  }, []);

  const accepted = consent === 'accepted';
  const showBanner = consent === null;

  return { accepted, accept, dismissEssential, showBanner };
}
