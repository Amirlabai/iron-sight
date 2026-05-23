import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Zap, Volume2, VolumeX, Radio, RotateCcw, Terminal, Shield, Bell } from 'lucide-react';
import AlertPreferencesWizard from './components/Onboarding/AlertPreferencesWizard';
import { Analytics } from '@vercel/analytics/react';
import { TacticalProvider } from './context/TacticalProvider';
import { useTactical } from './context/TacticalContext';
import MapViewer from './components/Map/MapViewer';
import Sidebar from './components/Sidebar/Sidebar';
import TacticalClock from './components/Header/TacticalClock';
import { useMobileLayout } from './hooks/useMobileLayout';
import { agentDebugLogThrottled } from './utils/agentDebugLog';
import {
  getLiveStatusPillAriaLabel,
  getLiveStatusPillLabel,
  getSandboxStatusPillLabel,
} from './utils/statusLabels';
import './styles/layout.css';
import './styles/animations.css';
import './App.css';

// --- Splash Screen (boot sequence) ---
function SplashScreen({ progress }) {
  return (
    <motion.div
      className="splash-screen"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
    >
      <div className="radar-scanner">
        <div className="sweep"></div>
        <img src="/favicon.png" className="splash-logo-img" alt="IRON SIGHT LOGO" />
      </div>
      <div className="boot-sequence">
        <div className="terminal-line"><Terminal size={14} /> ESTABLISHING SECURE UPLINK...</div>
        <div className="terminal-line"><Shield size={14} /> LOADING GEOGRAPHIC DATA...</div>
        {progress > 50 && <div className="terminal-line"><Activity size={14} /> CALIBRATING TRAJECTORY ENGINE...</div>}
        {progress > 80 && <div className="terminal-line"><Zap size={14} /> SYSTEM READY. STANDING BY.</div>}
      </div>
      <div className="progress-bar-container">
        <motion.div className="progress-bar" initial={{ scaleX: 0 }} animate={{ scaleX: progress / 100 }} />
      </div>
      <h2 className="splash-title">IRON SIGHT <span>{__APP_VERSION__}</span></h2>
    </motion.div>
  );
}

// --- App Shell (consumes TacticalContext) ---
function AppShell() {
  const {
    isReady, loadingProgress, liveEvents, viewMode,
    isConnected, isMuted, setIsMuted, tacticalHealth,
    returnToLive, setViewMode, setSandboxEvent,
    isSidebarExpanded,
    alertPrefs,
    alertPrefsApi,
  } = useTactical();

  const {
    showWizard,
    openWizard,
    closeWizard,
    skipOnboarding,
    requestNotificationPermission,
    requestGeolocation,
    completeOnboarding,
  } = alertPrefsApi;

  const isMobile = useMobileLayout();
  const iconSize = isMobile ? 18 : 20;
  const statusCompact = isMobile;

  React.useEffect(() => {
    if (typeof PerformanceObserver === 'undefined') return undefined;
    const obs = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration < 50) continue;
        // #region agent log
        agentDebugLogThrottled(
          'longtask',
          2000,
          'App.jsx:longtask',
          'main thread long task',
          { durationMs: Math.round(entry.duration), name: entry.name || 'unknown' },
          'D',
        );
        // #endregion
      }
    });
    try {
      obs.observe({ entryTypes: ['longtask'] });
    } catch {
      return undefined;
    }
    return () => obs.disconnect();
  }, []);

  return (
    <div className={`dashboard-container ${viewMode} ${isSidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
      <AnimatePresence>
        {!isReady && <SplashScreen key="splash" progress={loadingProgress} />}
      </AnimatePresence>

      {isReady && (
      <>
      <header className="premium-header">
        <div className="header-bar">
          <div className="logo-section">
            <img src="/favicon.png" className={`logo-img ${liveEvents.length > 0 ? 'alert-pulse' : ''}`} alt="IRON SIGHT" />
            <h1>IRON SIGHT</h1>
            <span className="version-badge">{viewMode === 'archive' ? 'ARCHIVE' : (viewMode === 'timeframe' ? 'TIMEFRAME' : __APP_VERSION__)}</span>
          </div>

          <TacticalClock />

          <div className="status-section">
          <button
            type="button"
            className={`icon-btn ${alertPrefs.scope !== 'all' ? 'icon-btn-active' : ''}`}
            onClick={openWizard}
            aria-label="Alert notification preferences"
          >
            <Bell size={iconSize} />
          </button>
          <button className="icon-btn" onClick={() => setIsMuted(!isMuted)} aria-label={isMuted ? "Unmute Tactical Audio" : "Mute Tactical Audio"}>
            {isMuted ? <VolumeX size={iconSize} /> : <Volume2 size={iconSize} />}
          </button>

          {(viewMode === 'archive' || viewMode === 'timeframe') && (
            <button className="return-live-btn header-return-live-btn" onClick={returnToLive} aria-label="Return to Live Tactical View">
              <Radio size={16} /> RETURN TO LIVE
            </button>
          )}

          {viewMode === 'live' && (
            <div
              className={`status-pill ${isConnected ? (tacticalHealth.status === 'DEGRADED' ? 'degraded' : 'online') : 'offline'}`}
              aria-label={getLiveStatusPillAriaLabel(isConnected, tacticalHealth)}
            >
              <div className="pulse-dot"></div>
              {getLiveStatusPillLabel(isConnected, tacticalHealth, { compact: statusCompact })}
            </div>
          )}

          {viewMode === 'sandbox' && (
            <div className="flex gap-2">
              <button className="return-live-btn sandbox" onClick={() => { setViewMode('live'); setSandboxEvent(null); }}>
                <RotateCcw size={16} /> TERMINATE ANALYSIS
              </button>
              <div className="status-pill sandbox" aria-label={getSandboxStatusPillLabel()}>
                <div className="pulse-dot"></div>
                {getSandboxStatusPillLabel({ compact: statusCompact })}
              </div>
            </div>
          )}
          </div>
        </div>
      </header>

      <AnimatePresence>
        {showWizard && (
          <AlertPreferencesWizard
            key="alert-prefs-wizard"
            prefs={alertPrefs}
            onClose={closeWizard}
            onSkip={skipOnboarding}
            requestNotificationPermission={requestNotificationPermission}
            requestGeolocation={requestGeolocation}
            completeOnboarding={completeOnboarding}
          />
        )}
      </AnimatePresence>

      <main className="main-content">
        <MapViewer />
        <Sidebar />
      </main>

      {(viewMode === 'archive' || viewMode === 'timeframe') && (
        <button
          type="button"
          className="return-to-live-btn sidebar-return-live"
          onClick={returnToLive}
          aria-label="Return to Live Tactical View"
        >
          RETURN TO LIVE
        </button>
      )}

      </>
      )}

      <Analytics />

      {/* Tactical SVG Filters */}
      <svg style={{ position: 'absolute', width: 0, height: 0 }}>
        <defs>
          <filter id="organic-round">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7" result="round" />
            <feComposite in="SourceGraphic" in2="round" operator="atop" />
          </filter>
        </defs>
      </svg>
    </div>
  );
}

// --- App Entry (TacticalProvider wrapper) ---
function App() {
  return (
    <TacticalProvider>
      <AppShell />
    </TacticalProvider>
  );
}

export default App;
