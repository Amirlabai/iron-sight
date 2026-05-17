import { getDistance } from './geoUtils';

const GEO_OPTIONS = {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 60000,
};

export function isGeolocationSupported() {
  return typeof navigator !== 'undefined' && 'geolocation' in navigator;
}

export function getUserPosition() {
  if (!isGeolocationSupported()) {
    return Promise.reject(new Error('Geolocation not supported'));
  }
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
      reject,
      GEO_OPTIONS
    );
  });
}

/**
 * @param {(loc: [number, number]) => void} onUpdate
 * @param {{ minDeltaM?: number }} options
 * @returns {() => void} cleanup
 */
export function watchUserPosition(onUpdate, options = {}) {
  const minDeltaKm = (options.minDeltaM ?? 500) / 1000;
  if (!isGeolocationSupported()) return () => {};

  let last = null;
  const id = navigator.geolocation.watchPosition(
    (pos) => {
      const loc = [pos.coords.latitude, pos.coords.longitude];
      if (last && getDistance(last, loc) < minDeltaKm) return;
      last = loc;
      onUpdate(loc);
    },
    (err) => {
      if (!import.meta.env.PROD) console.warn('GPS watch error:', err.message);
    },
    GEO_OPTIONS
  );

  return () => navigator.geolocation.clearWatch(id);
}
