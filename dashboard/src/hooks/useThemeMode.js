import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'iron-sight-theme-mode';
const DEFAULT_THEME = 'dark';

function normalizeTheme(value) {
  return value === 'light' ? 'light' : 'dark';
}

function readStoredTheme() {
  try {
    return normalizeTheme(localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_THEME;
  }
}

function applyTheme(themeMode) {
  const root = document.documentElement;
  const mode = normalizeTheme(themeMode);
  root.setAttribute('data-theme', mode);
}

export function useThemeMode() {
  const [themeMode, setThemeMode] = useState(() => {
    const stored = readStoredTheme();
    applyTheme(stored);
    return stored;
  });

  useEffect(() => {
    applyTheme(themeMode);
  }, [themeMode]);

  const toggleThemeMode = useCallback(() => {
    setThemeMode((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return {
    themeMode,
    isLightMode: themeMode === 'light',
    toggleThemeMode,
  };
}
