import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { isGeolocationSupported, getUserPosition, watchUserPosition } from './userLocation.js';

describe('isGeolocationSupported', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should return false when navigator is undefined', () => {
    vi.stubGlobal('navigator', undefined);
    expect(isGeolocationSupported()).toBe(false);
  });

  it('should return false when geolocation is missing', () => {
    vi.stubGlobal('navigator', {});
    expect(isGeolocationSupported()).toBe(false);
  });

  it('should return true when geolocation API exists', () => {
    vi.stubGlobal('navigator', { geolocation: {} });
    expect(isGeolocationSupported()).toBe(true);
  });
});

describe('getUserPosition', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should reject when geolocation is not supported', async () => {
    vi.stubGlobal('navigator', {});
    await expect(getUserPosition()).rejects.toThrow('Geolocation not supported');
  });

  it('should resolve with lat/lng on success', async () => {
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: (success) => {
          success({ coords: { latitude: 32.1, longitude: 34.2 } });
        },
      },
    });
    await expect(getUserPosition()).resolves.toEqual([32.1, 34.2]);
  });

  it('should reject when geolocation returns error', async () => {
    const err = new Error('denied');
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: (_s, reject) => reject(err),
      },
    });
    await expect(getUserPosition()).rejects.toBe(err);
  });
});

describe('watchUserPosition', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should return noop cleanup when geolocation is unsupported', () => {
    vi.stubGlobal('navigator', {});
    const cleanup = watchUserPosition(() => {});
    expect(typeof cleanup).toBe('function');
    expect(cleanup()).toBeUndefined();
  });

  it('should call onUpdate with coordinates and register clearWatch', () => {
    const onUpdate = vi.fn();
    const clearWatch = vi.fn();
    let watchId = 7;

    vi.stubGlobal('navigator', {
      geolocation: {
        watchPosition: (cb) => {
          cb({ coords: { latitude: 32.0, longitude: 34.0 } });
          return watchId;
        },
        clearWatch,
      },
    });

    const cleanup = watchUserPosition(onUpdate, { minDeltaM: 0 });
    expect(onUpdate).toHaveBeenCalledWith([32.0, 34.0]);
    cleanup();
    expect(clearWatch).toHaveBeenCalledWith(watchId);
  });

  it('should skip update when movement is below minDeltaM', () => {
    const onUpdate = vi.fn();
    vi.stubGlobal('navigator', {
      geolocation: {
        watchPosition: (cb) => {
          cb({ coords: { latitude: 32.0, longitude: 34.0 } });
          cb({ coords: { latitude: 32.00001, longitude: 34.00001 } });
          return 1;
        },
        clearWatch: vi.fn(),
      },
    });
    watchUserPosition(onUpdate, { minDeltaM: 5000 });
    expect(onUpdate).toHaveBeenCalledTimes(1);
  });
});
