import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('./constants.js', () => ({
  TACTICAL_API_URL: 'http://test.local',
}));

import {
  fetchVapidPublicKey,
  getServiceWorkerRegistration,
  subscribeToPush,
  syncPushSubscription,
  patchPushLocation,
} from './pushClient.js';

describe('fetchVapidPublicKey', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('should return env key when VITE_VAPID_PUBLIC_KEY is set', async () => {
    vi.stubEnv('VITE_VAPID_PUBLIC_KEY', 'env-key-base64');
    await expect(fetchVapidPublicKey()).resolves.toBe('env-key-base64');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('should fetch public key from API when env key missing', async () => {
    vi.stubEnv('VITE_VAPID_PUBLIC_KEY', '');
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ publicKey: 'api-key' }),
    });
    await expect(fetchVapidPublicKey()).resolves.toBe('api-key');
    expect(fetch).toHaveBeenCalledWith(
      'http://test.local/api/push/vapid-public-key',
      expect.any(Object)
    );
  });

  it('should throw when API response is not ok', async () => {
    vi.stubEnv('VITE_VAPID_PUBLIC_KEY', '');
    fetch.mockResolvedValue({ ok: false });
    await expect(fetchVapidPublicKey()).rejects.toThrow('VAPID key unavailable');
  });
});

describe('getServiceWorkerRegistration', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should throw when service worker is not supported', async () => {
    vi.stubGlobal('navigator', {});
    await expect(getServiceWorkerRegistration()).rejects.toThrow(
      'Service worker not supported'
    );
  });
});

describe('syncPushSubscription', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should return push_unavailable when server returns 503', async () => {
    fetch.mockResolvedValue({ status: 503 });
    const result = await syncPushSubscription({
      subscription: { endpoint: 'x' },
      scope: 'all',
      radiusKm: 10,
      location: null,
    });
    expect(result).toEqual({ ok: false, reason: 'push_unavailable' });
  });

  it('should return client token on success', async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ client_token: 'tok-abc' }),
    });
    const result = await syncPushSubscription({
      subscription: { endpoint: 'x' },
      scope: 'radius',
      radiusKm: 15,
      location: [32.0, 34.0],
    });
    expect(result).toEqual({ ok: true, clientToken: 'tok-abc' });
  });

  it('should throw with server error message when not ok', async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Invalid subscription' }),
    });
    await expect(
      syncPushSubscription({
        subscription: {},
        scope: 'all',
        radiusKm: 10,
        location: null,
      })
    ).rejects.toThrow('Invalid subscription');
  });
});

describe('patchPushLocation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should return ok false when endpoint or location missing', async () => {
    expect(await patchPushLocation(null, [32, 34], 'tok')).toEqual({ ok: false });
    expect(await patchPushLocation('ep', null, 'tok')).toEqual({ ok: false });
  });

  it('should return ok true when patch succeeds', async () => {
    fetch.mockResolvedValue({ ok: true, status: 200 });
    const result = await patchPushLocation('http://ep', [32.0, 34.0], 'tok');
    expect(result).toEqual({ ok: true });
  });
});

describe('subscribeToPush', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('should throw when PushManager is missing', async () => {
    vi.stubGlobal('navigator', {
      serviceWorker: {
        ready: Promise.resolve({
          pushManager: {},
        }),
      },
    });
    vi.stubGlobal('window', {});
    await expect(getServiceWorkerRegistration()).resolves.toBeDefined();
    const reg = await getServiceWorkerRegistration();
    vi.stubGlobal('navigator', { serviceWorker: { ready: Promise.resolve(reg) } });
    vi.stubGlobal('window', {});
    await expect(subscribeToPush('QUJD')).rejects.toThrow('Push not supported');
  });
});
