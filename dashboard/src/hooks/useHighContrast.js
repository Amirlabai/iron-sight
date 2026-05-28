import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'iron-sight-a11y-high-contrast';

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function applyToDocument(enabled) {
  const root = document.documentElement;
  if (enabled) {
    root.setAttribute('data-high-contrast', 'true');
  } else {
    root.removeAttribute('data-high-contrast');
  }
}

/** Apply persisted high contrast before React mounts (legal pages, prerender). */
export function initHighContrastFromStorage() {
  applyToDocument(readStored());
}

export function useHighContrast() {
  const [enabled, setEnabled] = useState(() => {
    const stored = readStored();
    applyToDocument(stored);
    return stored;
  });

  useEffect(() => {
    applyToDocument(enabled);
  }, [enabled]);

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      try {
        if (next) {
          localStorage.setItem(STORAGE_KEY, 'true');
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return { enabled, toggle };
}
