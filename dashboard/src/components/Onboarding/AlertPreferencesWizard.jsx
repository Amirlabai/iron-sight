import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, MapPin, Radio, Target, Crosshair, ChevronRight, X } from 'lucide-react';
import {
  DEFAULT_RADIUS_KM,
  RADIUS_MIN_KM,
  RADIUS_MAX_KM,
} from '../../utils/alertMatching';

const STEPS = ['notify', 'gps', 'scope', 'confirm'];

export default function AlertPreferencesWizard({
  prefs,
  onClose,
  onSkip,
  requestNotificationPermission,
  requestGeolocation,
  completeOnboarding,
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [scope, setScope] = useState(prefs.scope || 'all');
  const [radiusKm, setRadiusKm] = useState(prefs.radiusKm ?? DEFAULT_RADIUS_KM);
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [notifyStatus, setNotifyStatus] = useState(prefs.notifyPermission);
  const [geoStatus, setGeoStatus] = useState(prefs.geoPermission);

  const step = STEPS[stepIndex];
  const geoGranted = geoStatus === 'granted' || prefs.geoPermission === 'granted';
  const notifyGranted = notifyStatus === 'granted' || prefs.notifyPermission === 'granted';

  const next = () => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  const back = () => setStepIndex((i) => Math.max(i - 1, 0));

  const handleEnableNotify = async () => {
    setBusy(true);
    const r = await requestNotificationPermission();
    setNotifyStatus(r);
    setBusy(false);
    next();
  };

  const handleEnableGps = async () => {
    setBusy(true);
    try {
      await requestGeolocation();
      setGeoStatus('granted');
    } catch {
      setGeoStatus('denied');
    }
    setBusy(false);
    next();
  };

  const handleFinish = async () => {
    setBusy(true);
    setSaveError('');
    const effectiveScope =
      (scope === 'radius' || scope === 'exact') && !geoGranted ? 'all' : scope;
    try {
      const result = await completeOnboarding({ scope: effectiveScope, radiusKm });
      if (result && !result.ok) {
        const msg =
          result.reason === 'push_unavailable'
            ? 'Push service unavailable. Check server config or save again later.'
            : result.reason === 'notifications_denied'
              ? 'Notifications are off — enable them in system settings, then try again.'
              : result.reason || 'Could not register for background alerts.';
        setSaveError(msg);
      }
    } catch (err) {
      setSaveError(err?.message || 'Save failed. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      className="alert-prefs-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-prefs-title"
    >
      <motion.div
        className="alert-prefs-modal"
        initial={{ y: 24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
      >
        <button type="button" className="alert-prefs-close" onClick={onSkip} aria-label="Close">
          <X size={18} />
        </button>

        <div className="alert-prefs-steps">
          {STEPS.map((s, i) => (
            <span key={s} className={`alert-prefs-step-dot ${i <= stepIndex ? 'active' : ''}`} />
          ))}
        </div>

        {step === 'notify' && (
          <>
            <Bell size={32} className="alert-prefs-icon" />
            <h2 id="alert-prefs-title">Background alerts</h2>
            <p className="alert-prefs-desc">
              Enable notifications so Iron Sight can warn you when alerts match your rules, even when the app is closed.
            </p>
            <button type="button" className="alert-prefs-primary" disabled={busy} onClick={handleEnableNotify}>
              Enable notifications
            </button>
            <button type="button" className="alert-prefs-secondary" onClick={next}>
              Not now <ChevronRight size={14} />
            </button>
          </>
        )}

        {step === 'gps' && (
          <>
            <MapPin size={32} className="alert-prefs-icon" />
            <h2 id="alert-prefs-title">Your location</h2>
            <p className="alert-prefs-desc">
              GPS is used only on your device and our server to filter alerts by distance. We do not store your name or identity.
            </p>
            <button type="button" className="alert-prefs-primary" disabled={busy} onClick={handleEnableGps}>
              Enable location
            </button>
            <button type="button" className="alert-prefs-secondary" onClick={next}>
              Skip for now <ChevronRight size={14} />
            </button>
          </>
        )}

        {step === 'scope' && (
          <>
            <Target size={32} className="alert-prefs-icon" />
            <h2 id="alert-prefs-title">Alert scope</h2>
            <p className="alert-prefs-desc">Choose which threats should trigger sound and push alerts.</p>

            <div className="alert-prefs-options" role="radiogroup" aria-label="Alert scope">
              <label className={`alert-prefs-option ${scope === 'all' ? 'selected' : ''}`}>
                <input type="radio" name="scope" value="all" checked={scope === 'all'} onChange={() => setScope('all')} />
                <Radio size={18} />
                <span>
                  <strong>All alerts</strong>
                  <small>Every live threat nationwide</small>
                </span>
              </label>

              <label
                className={`alert-prefs-option ${scope === 'radius' ? 'selected' : ''} ${!geoGranted ? 'disabled' : ''}`}
              >
                <input
                  type="radio"
                  name="scope"
                  value="radius"
                  checked={scope === 'radius'}
                  disabled={!geoGranted}
                  onChange={() => setScope('radius')}
                />
                <MapPin size={18} />
                <span>
                  <strong>Near me (radius)</strong>
                  <small>Alerts within your chosen distance</small>
                </span>
              </label>

              {scope === 'radius' && geoGranted && (
                <div className="alert-prefs-slider-wrap">
                  <label htmlFor="radius-km">Radius: {radiusKm} km</label>
                  <input
                    id="radius-km"
                    type="range"
                    min={RADIUS_MIN_KM}
                    max={RADIUS_MAX_KM}
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(Number(e.target.value))}
                  />
                </div>
              )}

              <label
                className={`alert-prefs-option ${scope === 'exact' ? 'selected' : ''} ${!geoGranted ? 'disabled' : ''}`}
              >
                <input
                  type="radio"
                  name="scope"
                  value="exact"
                  checked={scope === 'exact'}
                  disabled={!geoGranted}
                  onChange={() => setScope('exact')}
                />
                <Crosshair size={18} />
                <span>
                  <strong>Exact location</strong>
                  <small>Only when you are inside the alert area</small>
                </span>
              </label>
            </div>

            <button type="button" className="alert-prefs-primary" onClick={next}>
              Continue <ChevronRight size={14} />
            </button>
            {stepIndex > 0 && (
              <button type="button" className="alert-prefs-secondary" onClick={back}>
                Back
              </button>
            )}
          </>
        )}

        {step === 'confirm' && (
          <>
            <ShieldIcon />
            <h2 id="alert-prefs-title">Confirm</h2>
            <ul className="alert-prefs-summary">
              <li>Notifications: {notifyGranted ? 'On' : 'Off (in-app only)'}</li>
              <li>Location: {geoGranted ? 'On' : 'Off'}</li>
              <li>
                Scope:{' '}
                {scope === 'all' && 'All alerts'}
                {scope === 'radius' && geoGranted && `Within ${radiusKm} km`}
                {scope === 'radius' && !geoGranted && 'All alerts (GPS required for radius)'}
                {scope === 'exact' && geoGranted && 'Exact location only'}
                {scope === 'exact' && !geoGranted && 'All alerts (GPS required for exact)'}
              </li>
            </ul>
            {saveError && <p className="alert-prefs-error" role="alert">{saveError}</p>}
            <button type="button" className="alert-prefs-primary" disabled={busy} onClick={handleFinish}>
              {busy ? 'Saving…' : 'Save preferences'}
            </button>
            <button type="button" className="alert-prefs-secondary" onClick={back}>
              Back
            </button>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}

function ShieldIcon() {
  return (
    <svg className="alert-prefs-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}
