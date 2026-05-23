import { useState, useEffect, useCallback, useRef } from 'react';
import { DEFAULT_RADIUS_KM } from '../utils/alertMatching';
import {
  fetchVapidPublicKey,
  subscribeToPush,
  syncPushSubscription,
  patchPushLocation,
  unsubscribeFromPush,
} from '../utils/pushClient';
import { getUserPosition, watchUserPosition, isGeolocationSupported } from '../utils/userLocation';

const STORAGE_KEY = 'iron_sight_alert_prefs';

const DEFAULT_PREFS = {
  complete: false,
  notifyPermission: 'default',
  geoPermission: 'denied',
  scope: 'all',
  radiusKm: DEFAULT_RADIUS_KM,
  location: null,
  locationUpdatedAt: null,
  pushEndpoint: null,
  pushClientToken: null,
  wizardDismissed: false,
};

function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

function savePrefs(prefs) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function useAlertPreferences() {
  const [prefs, setPrefsState] = useState(loadPrefs);
  const [showWizard, setShowWizard] = useState(false);
  const prefsRef = useRef(prefs);

  useEffect(() => {
    prefsRef.current = prefs;
  }, [prefs]);

  const setPrefs = useCallback((patch) => {
    setPrefsState((prev) => {
      const next = typeof patch === 'function' ? patch(prev) : { ...prev, ...patch };
      savePrefs(next);
      return next;
    });
  }, []);

  const openWizard = useCallback(() => setShowWizard(true), []);
  const closeWizard = useCallback(() => setShowWizard(false), []);

  const requestNotificationPermission = useCallback(async () => {
    if (!('Notification' in window)) {
      setPrefs({ notifyPermission: 'denied' });
      return 'denied';
    }
    const result = await Notification.requestPermission();
    setPrefs({ notifyPermission: result });
    return result;
  }, [setPrefs]);

  const requestGeolocation = useCallback(async () => {
    if (!isGeolocationSupported()) {
      setPrefs({ geoPermission: 'denied' });
      return null;
    }
    try {
      const loc = await getUserPosition();
      setPrefs({
        geoPermission: 'granted',
        location: loc,
        locationUpdatedAt: new Date().toISOString(),
      });
      return loc;
    } catch {
      setPrefs({ geoPermission: 'denied' });
      return null;
    }
  }, [setPrefs]);

  const registerPush = useCallback(
    async ({ scope, radiusKm, location } = {}) => {
      const current = prefsRef.current;
      const effectiveScope = scope ?? current.scope;
      const effectiveRadius = radiusKm ?? current.radiusKm;
      const effectiveLoc = location ?? current.location;

      if (current.notifyPermission !== 'granted') {
        return { ok: false, reason: 'notifications_denied' };
      }

      const basePatch = {
        scope: effectiveScope,
        radiusKm: effectiveRadius,
        location: effectiveLoc,
      };

      try {
        const vapidKey = await fetchVapidPublicKey();
        const subscription = await subscribeToPush(vapidKey);
        const syncResult = await syncPushSubscription({
          subscription,
          scope: effectiveScope,
          radiusKm: effectiveRadius,
          location: effectiveLoc,
        });

        if (!syncResult.ok) {
          setPrefs({
            ...basePatch,
            pushEndpoint: subscription.endpoint,
            complete: false,
          });
          return syncResult;
        }

        setPrefs({
          ...basePatch,
          pushEndpoint: subscription.endpoint,
          pushClientToken: syncResult.clientToken,
          complete: true,
          wizardDismissed: true,
        });

        return syncResult;
      } catch (err) {
        if (!import.meta.env.PROD) console.warn('Push registration failed:', err);
        const swNotReady =
          typeof err?.message === 'string' &&
          (err.message.includes('Service worker') || err.message.includes('service worker'));
        if (swNotReady) {
          setPrefs({
            ...basePatch,
            complete: true,
            wizardDismissed: true,
          });
          return {
            ok: false,
            reason: 'push_sw_pending',
            message: err.message,
          };
        }
        setPrefs({
          ...basePatch,
          complete: false,
        });
        return { ok: false, reason: err.message };
      }
    },
    [setPrefs]
  );

  const completeOnboarding = useCallback(
    async ({ scope, radiusKm, skipPush = false }) => {
      let loc = prefsRef.current.location;
      if ((scope === 'radius' || scope === 'exact') && !loc) {
        loc = await requestGeolocation();
      }

      const basePatch = {
        scope,
        radiusKm,
        location: loc,
        wizardDismissed: true,
      };

      if (!skipPush && prefsRef.current.notifyPermission === 'granted') {
        const result = await registerPush({ scope, radiusKm, location: loc });
        if (!result.ok) {
          if (result.reason === 'push_sw_pending') {
            closeWizard();
            return { ok: true, pushDeferred: true };
          }
          setPrefs({ ...basePatch, complete: false });
          return result;
        }
      } else {
        setPrefs({ ...basePatch, complete: true });
      }
      closeWizard();
      return { ok: true };
    },
    [registerPush, requestGeolocation, setPrefs, closeWizard]
  );

  const skipOnboarding = useCallback(() => {
    setPrefs({ wizardDismissed: true, complete: false });
    closeWizard();
  }, [setPrefs, closeWizard]);

  useEffect(() => {
    if (!prefs.geoPermission || prefs.geoPermission === 'denied') return undefined;
    if (!prefs.location) return undefined;

    return watchUserPosition((loc) => {
      setPrefs({
        location: loc,
        locationUpdatedAt: new Date().toISOString(),
      });
      const { pushEndpoint, pushClientToken } = prefsRef.current;
      if (pushEndpoint) {
        patchPushLocation(pushEndpoint, loc, pushClientToken);
      }
    });
  }, [prefs.geoPermission, prefs.location, setPrefs]);

  return {
    prefs,
    setPrefs,
    showWizard,
    setShowWizard,
    openWizard,
    closeWizard,
    requestNotificationPermission,
    requestGeolocation,
    registerPush,
    completeOnboarding,
    skipOnboarding,
    unsubscribeFromPush,
  };
}

export function shouldShowAlertWizard(isReady, prefs) {
  if (!isReady) return false;
  if (prefs.complete || prefs.wizardDismissed) return false;
  return true;
}
