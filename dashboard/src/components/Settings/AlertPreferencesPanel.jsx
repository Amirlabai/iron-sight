import React, { useCallback, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import {
  DEFAULT_RADIUS_KM,
  RADIUS_MIN_KM,
  RADIUS_MAX_KM,
} from '../../utils/alertMatching';
import {
  DEFAULT_MAP_ZOOM_LEVELS,
  MAP_ZOOM_LEVEL_SECTIONS,
  MAP_ZOOM_LEVEL_LABELS,
  getAllMapZoomLevelKeys,
  mergeMapZoomLevels,
  parseZoomDraft,
} from '../../utils/mapZoomLevels';
import PreferenceSwitch from './PreferenceSwitch';
import './AlertPreferencesPanel.css';

export default function AlertPreferencesPanel({
  prefs,
  onClose,
  setPrefs,
  flushPersistPrefs,
  requestNotificationPermission,
  requestGeolocation,
  syncPushFromPrefs,
}) {
  const overlayRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const zoomKeys = useMemo(() => getAllMapZoomLevelKeys(), []);

  const levelsToDraftStrings = useCallback(
    (levels) => Object.fromEntries(zoomKeys.map((key) => [key, String(levels[key])])),
    [zoomKeys],
  );

  const [draftZoom, setDraftZoom] = useState(() =>
    levelsToDraftStrings(mergeMapZoomLevels(prefs.mapZoomLevels)),
  );
  const draftZoomRef = useRef(draftZoom);
  draftZoomRef.current = draftZoom;

  const commitAllZoomDrafts = useCallback(() => {
    const saved = mergeMapZoomLevels(prefs.mapZoomLevels);
    const draft = draftZoomRef.current;
    const patch = {};
    for (const key of zoomKeys) {
      patch[key] = parseZoomDraft(draft[key], saved[key]);
    }
    const next = { ...saved, ...patch };
    setPrefs({ mapZoomLevels: next });
    setDraftZoom(levelsToDraftStrings(next));
  }, [prefs.mapZoomLevels, setPrefs, zoomKeys, levelsToDraftStrings]);

  const handleClose = useCallback(() => {
    commitAllZoomDrafts();
    flushPersistPrefs?.();
    onClose();
  }, [commitAllZoomDrafts, flushPersistPrefs, onClose]);

  useFocusTrap(overlayRef, { active: true, onEscape: handleClose });

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
      setPrefs(
        { geoPermission: 'denied', location: null, locationUpdatedAt: null },
        { includeLocation: true },
      );
    }
    setBusy(false);
    syncPushFromPrefs?.();
  };

  const handleMapPinToggle = (on) => {
    setPrefs({ showUserLocationOnMap: on });
  };

  const normalizeZoomDraftKey = useCallback(
    (key, raw) => {
      const saved = mergeMapZoomLevels(prefs.mapZoomLevels);
      const value = parseZoomDraft(raw, saved[key]);
      setDraftZoom((prev) => ({ ...prev, [key]: String(value) }));
    },
    [prefs.mapZoomLevels],
  );

  const handleZoomReset = () => {
    const defaults = { ...DEFAULT_MAP_ZOOM_LEVELS };
    setPrefs({ mapZoomLevels: defaults });
    setDraftZoom(levelsToDraftStrings(defaults));
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

  const renderZoomField = (key) => (
    <div key={key} className="alert-prefs-panel__zoom-level-row">
      <label htmlFor={`pref-zoom-${key}`}>{MAP_ZOOM_LEVEL_LABELS[key]}</label>
      <input
        id={`pref-zoom-${key}`}
        type="text"
        inputMode="numeric"
        className="alert-prefs-panel__zoom-input"
        autoComplete="off"
        value={draftZoom[key] ?? ''}
        aria-describedby="pref-map-zoom-levels-label"
        onChange={(e) => setDraftZoom((prev) => ({ ...prev, [key]: e.target.value }))}
        onBlur={(e) => normalizeZoomDraftKey(key, e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
      />
    </div>
  );

  return (
    <div
      ref={overlayRef}
      className="alert-prefs-overlay alert-prefs-panel-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-prefs-panel-title"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="alert-prefs-panel">
        <header className="alert-prefs-panel__header">
          <h2 id="alert-prefs-panel-title">Preferences</h2>
          <button
            type="button"
            className="alert-prefs-close"
            onClick={handleClose}
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

          <div className="alert-prefs-panel__zoom-levels" aria-labelledby="pref-map-zoom-levels-label">
            <p id="pref-map-zoom-levels-label" className="alert-prefs-panel__zoom-levels-title">
              Map zoom levels
            </p>
            <p className="alert-prefs-panel__zoom-levels-desc">
              Leaflet zoom 4–14. Live map picks the value for the active threat type or launch country.
            </p>
            <div className="alert-prefs-panel__zoom-actions">
              <button
                type="button"
                className="alert-prefs-panel__zoom-reset"
                onClick={handleZoomReset}
              >
                Reset to defaults
              </button>
            </div>
            <div className="alert-prefs-panel__zoom-levels-list">
              {MAP_ZOOM_LEVEL_SECTIONS.map((section) => (
                <section
                  key={section.id}
                  className={`alert-prefs-panel__zoom-section alert-prefs-panel__zoom-section--${section.id}`}
                  aria-labelledby={`pref-zoom-section-${section.id}`}
                >
                  <h3 id={`pref-zoom-section-${section.id}`} className="alert-prefs-panel__zoom-section-title">
                    {section.title}
                  </h3>
                  <div className="alert-prefs-panel__zoom-section-body">
                    {section.groups.map((group) => (
                      <div
                        key={group.join('-')}
                        className={
                          group.length === 1
                            ? 'alert-prefs-panel__zoom-group alert-prefs-panel__zoom-group--full'
                            : 'alert-prefs-panel__zoom-group alert-prefs-panel__zoom-group--pair'
                        }
                      >
                        {group.map((key) => renderZoomField(key))}
                      </div>
                    ))}
                  </div>
                </section>
              ))}
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
