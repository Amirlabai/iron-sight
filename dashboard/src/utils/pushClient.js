import { TACTICAL_API_URL } from './constants';

const PUSH_TOKEN_HEADER = 'X-Push-Client-Token';
const SW_READY_MS = 12000;
const FETCH_MS = 15000;

function withTimeout(promise, ms, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(message)), ms);
    }),
  ]);
}

async function fetchWithTimeout(url, options = {}) {
  const res = await withTimeout(
    fetch(url, options),
    FETCH_MS,
    'Request timed out — check connection and try again'
  );
  return res;
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
  return out;
}

function pushHeaders(clientToken) {
  const headers = { 'Content-Type': 'application/json' };
  if (clientToken) headers[PUSH_TOKEN_HEADER] = clientToken;
  return headers;
}

export async function fetchVapidPublicKey() {
  const envKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
  if (envKey) return envKey;

  const res = await fetchWithTimeout(`${TACTICAL_API_URL}/api/push/vapid-public-key`);
  if (!res.ok) throw new Error('VAPID key unavailable');
  const data = await res.json();
  return data.publicKey;
}

export async function getServiceWorkerRegistration() {
  if (!('serviceWorker' in navigator)) throw new Error('Service worker not supported');
  return withTimeout(
    navigator.serviceWorker.ready,
    SW_READY_MS,
    'Service worker not ready — reload the page or use the installed app'
  );
}

export async function subscribeToPush(vapidPublicKey) {
  const reg = await getServiceWorkerRegistration();
  if (!('PushManager' in window)) throw new Error('Push not supported');

  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });
  }
  return sub.toJSON();
}

export async function unsubscribeFromPush(endpoint, clientToken) {
  const reg = await getServiceWorkerRegistration();
  const sub = await reg.pushManager.getSubscription();
  if (sub) {
    const ep = endpoint || sub.endpoint;
    await sub.unsubscribe();
    await fetch(`${TACTICAL_API_URL}/api/push/unsubscribe`, {
      method: 'DELETE',
      headers: pushHeaders(clientToken),
      body: JSON.stringify({ endpoint: ep, client_token: clientToken }),
    }).catch(() => {});
    return ep;
  }
  return null;
}

export async function syncPushSubscription({ subscription, scope, radiusKm, location }) {
  const res = await fetchWithTimeout(`${TACTICAL_API_URL}/api/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      subscription,
      scope,
      radius_km: radiusKm,
      location: location ? { lat: location[0], lng: location[1] } : null,
    }),
  });
  if (res.status === 503) return { ok: false, reason: 'push_unavailable' };
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Subscribe failed (${res.status})`);
  }
  const data = await res.json().catch(() => ({}));
  return { ok: true, clientToken: data.client_token };
}

export async function patchPushLocation(endpoint, location, clientToken) {
  if (!endpoint || !location) return { ok: false };
  const body = {
    endpoint,
    location: { lat: location[0], lng: location[1] },
    client_token: clientToken,
  };

  const attempt = async () => {
    const res = await fetch(`${TACTICAL_API_URL}/api/push/location`, {
      method: 'PATCH',
      headers: pushHeaders(clientToken),
      body: JSON.stringify(body),
    });
    return res;
  };

  let res = await attempt();
  if (!res.ok && res.status >= 500) {
    res = await attempt();
  }
  if (!res.ok && !import.meta.env.PROD) {
    console.warn('patchPushLocation failed:', res.status, endpoint);
  }
  return { ok: res.ok };
}
