import React, { useRef, useState } from 'react';
import { X } from 'lucide-react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import {
  DEFAULT_RADIUS_KM,
  RADIUS_MIN_KM,
  RADIUS_MAX_KM,
} from '../../utils/alertMatching';
import PreferenceSwitch from './PreferenceSwitch';
import './AlertPreferencesPanel.css';

export default function AlertPreferencesPanel({
  prefs,
  onClose,
  setPrefs,
  requestNotificationPermission,
  requestGeolocation,
  syncPushFromPrefs,
}) {
  const overlayRef = useRef(null);
  const [busy, setBusy] = useState(false);

  useFocusTrap(overlayRef, { active: true, onEscape: onClose });

  const notifyGranted =
    prefs.notifyPermission === 'granted' ||
    (typeof Notification !== 'undefined' && Notification.permission === 'granted');
  const geoGranted = prefs.geoPermission === 'granted';

  const handleNotifyToggle = async (on) => {
    if (!on) return;
    setBusy(true);
    await requestNotificationPermission();
    setBusy(false);
    syncPushFromPrefs?.();
  };

  const handleGeoToggle = async (on) => {
    setBusy(true);
    if (on) {
      await requestGeolocation();
    } else {
      setPrefs({ geoPermission: 'denied', location: null, locationUpdatedAt: null });
    }
    setBusy(false);
    syncPushFromPrefs?.();
  };

  const handleMapPinToggle = (on) => {
    setPrefs({ showUserLocationOnMap: on });
  };

  const handleScopeChange = (scope) => {
    const effective =
      (scope === 'radius' || scope === 'exact') && !geoGranted ? 'all' : scope;
    setPrefs({ scope: effective });
    syncPushFromPrefs?.();
  };

  const handleRadiusChange = (radiusKm) => {
    setPrefs({ radiusKm });
    syncPushFromPrefs?.();
  };

  return (
    <div
      ref={overlayRef}
      className="alert-prefs-overlay alert-prefs-panel-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-prefs-panel-title"
    >
      <div className="alert-prefs-panel">
        <header className="alert-prefs-panel__header">
          <h2 id="alert-prefs-panel-title">Preferences</h2>
          <button
            type="button"
            className="alert-prefs-close"
            onClick={onClose}
            aria-label="Close preferences"
          >
            <X size={18} />
          </button>
        </header>

        <div className="alert-prefs-panel__body">
          <div className="alert-prefs-panel__row">
            <div className="alert-prefs-panel__label" id="pref-notify-label">
              <strong>Background notifications</strong>
              <small>Alerts when the app is in the background</small>
              {!notifyGranted && prefs.notifyPermission === 'denied' ? (
                <small className="alert-prefs-panel__hint">
                  Blocked in browser settings. Enable there, then turn on here.
                </small>
              ) : null}
            </div>
            <div className="alert-prefs-panel__control">
              <PreferenceSwitch
                id="pref-notify"
                label="Background notifications"
                checked={notifyGranted}
                disabled={busy || notifyGranted}
                onChange={handleNotifyToggle}
              />
            </div>
          </div>

          <div className="alert-prefs-panel__row">
            <div className="alert-prefs-panel__label" id="pref-geo-label">
              <strong>Use my location</strong>
              <small>Filter alerts by distance on this device</small>
            </div>
            <div className="alert-prefs-panel__control">
              <PreferenceSwitch
                id="pref-geo"
                label="Use my location"
                checked={geoGranted}
                disabled={busy}
                onChange={handleGeoToggle}
              />
            </div>
          </div>

          <div className="alert-prefs-panel__row">
            <div className="alert-prefs-panel__label" id="pref-map-label">
              <strong>Show my position on map</strong>
              <small>Blue dot when you are inside Israel</small>
            </div>
            <div className="alert-prefs-panel__control">
              <PreferenceSwitch
                id="pref-map-pin"
                label="Show my position on map"
                checked={prefs.showUserLocationOnMap !== false}
                disabled={!geoGranted}
                onChange={handleMapPinToggle}
              />
            </div>
          </div>

          <div className="alert-prefs-panel__row alert-prefs-panel__row--scope">
            <div className="alert-prefs-panel__label" id="pref-scope-label">
              <strong>Alert scope</strong>
              <small>Which threats trigger sound and push</small>
            </div>
            <div className="alert-prefs-panel__control alert-prefs-panel__scope">
              <select
                id="pref-scope"
                className="alert-prefs-panel__select"
                value={prefs.scope || 'all'}
                aria-labelledby="pref-scope-label"
                onChange={(e) => handleScopeChange(e.target.value)}
              >
                <option value="all">All alerts nationwide</option>
                <option value="radius" disabled={!geoGranted}>
                  Near me (radius){!geoGranted ? ' — requires location' : ''}
                </option>
                <option value="exact" disabled={!geoGranted}>
                  Exact location only{!geoGranted ? ' — requires location' : ''}
                </option>
              </select>
            </div>
          </div>

          {prefs.scope === 'radius' && geoGranted ? (
            <div className="alert-prefs-panel__row alert-prefs-panel__row--slider">
              <div className="alert-prefs-panel__label">
                <label htmlFor="pref-radius-km">Alert radius: {prefs.radiusKm ?? DEFAULT_RADIUS_KM} km</label>
              </div>
              <div className="alert-prefs-panel__control alert-prefs-panel__control--full">
                <input
                  id="pref-radius-km"
                  type="range"
                  min={RADIUS_MIN_KM}
                  max={RADIUS_MAX_KM}
                  value={prefs.radiusKm ?? DEFAULT_RADIUS_KM}
                  onChange={(e) => handleRadiusChange(Number(e.target.value))}
                />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
