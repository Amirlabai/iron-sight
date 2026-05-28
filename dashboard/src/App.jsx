import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Activity, Zap, Volume2, VolumeX, Radio, RotateCcw, Terminal, Shield, Sun, Moon, ChevronUp } from 'lucide-react';
import HeaderSettingsControl from './components/HeaderSettingsControl';
import { Analytics } from '@vercel/analytics/react';
import AlertPreferencesWizard from './components/Onboarding/AlertPreferencesWizard';
import AlertPreferencesPanel from './components/Settings/AlertPreferencesPanel';
import { shouldShowAlertWizard } from './hooks/useAlertPreferences';
import SEO from './components/SEO';
import SiteFooter from './components/SiteFooter';
import CookieNotice from './components/CookieNotice';
import AccessibilityToolbar from './components/AccessibilityToolbar';
import { TacticalProvider } from './context/TacticalProvider';
import { useTactical } from './context/TacticalContext';
import MapViewer from './components/Map/MapViewer';
import Sidebar from './components/Sidebar/Sidebar';
import TacticalClock from './components/Header/TacticalClock';
import { useMobileLayout } from './hooks/useMobileLayout';
import { useCookieConsent } from './hooks/useCookieConsent';
import { agentDebugLogThrottled } from './utils/agentDebugLog';
import {
  getLiveStatusPillAriaLabel,
  getLiveStatusPillLabel,
  getSandboxStatusPillLabel,
} from './utils/statusLabels';
import About from './pages/About';
import Accessibility from './pages/Accessibility';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import NotFound from './pages/NotFound';
import './styles/layout.css';
import './styles/animations.css';
import './styles/a11y-high-contrast.css';
import './App.css';

function SplashScreen({ progress }) {
  return (
    <div className="splash-screen" role="status" aria-live="polite" aria-busy="true">
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
        <div className="progress-bar" style={{ transform: `scaleX(${Math.min(100, Math.max(0, progress)) / 100})` }} />
      </div>
      <h2 className="splash-title">IRON SIGHT <span>{__APP_VERSION__}</span></h2>
    </div>
  );
}

function TacticalDashboard() {
  const {
    accepted: cookieAccepted,
    accept: acceptCookies,
    dismissEssential: dismissCookies,
    showBanner,
  } = useCookieConsent();

  const {
    isReady, loadingProgress, liveEvents, viewMode,
    isConnected, isMuted, setIsMuted, tacticalHealth,
    returnToLive, setViewMode, setSandboxEvent,
    isSidebarExpanded,
    alertPrefs,
    alertPrefsApi,
    isLightMode,
    toggleThemeMode,
  } = useTactical();

  const {
    showWizard,
    openWizard,
    showPreferencesPanel,
    openPreferencesPanel,
    closePreferencesPanel,
    skipOnboarding,
    requestNotificationPermission,
    requestGeolocation,
    completeOnboarding,
    setPrefs,
    syncPushFromPrefs,
    flushPersistPrefs,
  } = alertPrefsApi;

  const isMobile = useMobileLayout();
  const iconSize = isMobile ? 18 : 20;
  const statusCompact = isMobile;

  React.useEffect(() => {
    if (shouldShowAlertWizard(isReady, alertPrefs)) {
      openWizard();
    }
  }, [isReady, alertPrefs.complete, alertPrefs.wizardDismissed, openWizard]);

  React.useEffect(() => {
    if (typeof PerformanceObserver === 'undefined') return undefined;
    const obs = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration < 50) continue;
        agentDebugLogThrottled(
          'longtask',
          2000,
          'App.jsx:longtask',
          'main thread long task',
          { durationMs: Math.round(entry.duration), name: entry.name || 'unknown' },
          'D',
        );
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
    <>
      <SEO pathname="/" includeWebApp breadcrumbs={[{ name: 'Home', url: '/' }]} />
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <div className={`dashboard-container ${viewMode} ${isSidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
        <header className="premium-header" aria-hidden={!isReady}>
          <div className="header-bar">
            <div className="logo-section">
              <img src="/favicon.png" className={`logo-img ${liveEvents.length > 0 ? 'alert-pulse' : ''}`} alt="IRON SIGHT" />
              <h1>IRON SIGHT</h1>
              <span className="version-badge">{viewMode === 'archive' ? 'ARCHIVE' : (viewMode === 'timeframe' ? 'TIMEFRAME' : __APP_VERSION__)}</span>
            </div>

            <TacticalClock />

            <div className="status-section">
              <HeaderSettingsControl
                isMobile={isMobile}
                iconSize={iconSize}
                prefsActive={alertPrefs.scope !== 'all'}
                onOpenPreferences={openPreferencesPanel}
                isLightMode={isLightMode}
                onToggleThemeMode={toggleThemeMode}
              />
              {!isMobile ? (
                <button
                  type="button"
                  className="icon-btn"
                  onClick={toggleThemeMode}
                  aria-label={isLightMode ? 'Switch to dark mode' : 'Switch to light mode'}
                >
                  {isLightMode ? <Moon size={iconSize} /> : <Sun size={iconSize} />}
                </button>
              ) : null}
              <button type="button" className="icon-btn" onClick={() => setIsMuted(!isMuted)} aria-label={isMuted ? 'Unmute Tactical Audio' : 'Mute Tactical Audio'}>
                {isMuted ? <VolumeX size={iconSize} /> : <Volume2 size={iconSize} />}
              </button>

              {(viewMode === 'archive' || viewMode === 'timeframe') && (
                <button type="button" className="return-live-btn header-return-live-btn" onClick={returnToLive} aria-label="Return to Live Tactical View">
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
                  <button type="button" className="return-live-btn sandbox" onClick={() => { setViewMode('live'); setSandboxEvent(null); }}>
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

        <main id="main-content" className="main-content" aria-hidden={!isReady}>
          <MapViewer />
          <Sidebar />
        </main>

        <SiteFooter compact />

        {(viewMode === 'archive' || viewMode === 'timeframe') && isReady && (
          <button
            type="button"
            className="return-to-live-btn sidebar-return-live"
            onClick={returnToLive}
            aria-label="Return to Live Tactical View"
          >
            RETURN TO LIVE
          </button>
        )}

        {showWizard && (
          <AlertPreferencesWizard
            prefs={alertPrefs}
            onSkip={skipOnboarding}
            requestNotificationPermission={requestNotificationPermission}
            requestGeolocation={requestGeolocation}
            completeOnboarding={completeOnboarding}
          />
        )}

        {showPreferencesPanel && (
          <AlertPreferencesPanel
            prefs={alertPrefs}
            onClose={closePreferencesPanel}
            setPrefs={setPrefs}
            flushPersistPrefs={flushPersistPrefs}
            requestNotificationPermission={requestNotificationPermission}
            requestGeolocation={requestGeolocation}
            syncPushFromPrefs={syncPushFromPrefs}
          />
        )}

        {!isReady && <SplashScreen progress={loadingProgress} />}

        <svg style={{ position: 'absolute', width: 0, height: 0 }} aria-hidden="true">
          <defs>
            <filter id="organic-round">
              <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
              <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7" result="round" />
              <feComposite in="SourceGraphic" in2="round" operator="atop" />
            </filter>
          </defs>
        </svg>
      </div>


      {!isSidebarExpanded && isMobile && (
        <button
          type="button"
          className="sidebar-expand-btn"
          onClick={(e) => { e.stopPropagation(); setIsSidebarExpanded(true); }}
          onPointerDown={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onMouseUp={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
          onTouchEnd={(e) => e.stopPropagation()}
          aria-label="Expand Sidebar"
        >
          <ChevronUp size={24} />
        </button>
      )}
      <AccessibilityToolbar />

      <CookieNotice
        show={showBanner}
        onAccept={acceptCookies}
        onEssentialOnly={dismissCookies}
      />
      {cookieAccepted ? <Analytics /> : null}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={(
            <TacticalProvider>
              <TacticalDashboard />
            </TacticalProvider>
          )}
        />
        <Route path="/about" element={<About />} />
        <Route path="/accessibility" element={<Accessibility />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
