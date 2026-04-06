import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Zap, Volume2, VolumeX, Radio, RotateCcw, Terminal, Shield } from 'lucide-react';
import { Analytics } from '@vercel/analytics/react';
import { TacticalProvider, useTactical } from './context/TacticalContext';
import MapViewer from './components/Map/MapViewer';
import Sidebar from './components/Sidebar/Sidebar';
import './styles/layout.css';
import './styles/animations.css';
import './App.css';

// --- Splash Screen (boot sequence) ---
function SplashScreen({ progress }) {
  return (
    <motion.div
      className="splash-screen"
      exit={{ opacity: 0, scale: 1.1 }}
      transition={{ duration: 1, ease: "circOut" }}
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
        <motion.div className="progress-bar" initial={{ width: 0 }} animate={{ width: `${progress}%` }} />
      </div>
      <h1 className="splash-title">IRON SIGHT <span>{__APP_VERSION__}</span></h1>
    </motion.div>
  );
}

// --- App Shell (consumes TacticalContext) ---
function AppShell() {
  const {
    isReady, loadingProgress, liveEvents, viewMode,
    isConnected, isMuted, setIsMuted, tacticalHealth,
    returnToLive, setViewMode, setSandboxEvent,
    isSidebarExpanded
  } = useTactical();

  return (
    <div className={`dashboard-container ${viewMode} ${isSidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
      <AnimatePresence>
        {!isReady && <SplashScreen progress={loadingProgress} />}
      </AnimatePresence>

      <header className="premium-header">
        <div className="logo-section">
          <img src="/favicon.png" className={`logo-img ${liveEvents.length > 0 ? 'alert-pulse' : ''}`} alt="IRON SIGHT" />
          <h1>IRON SIGHT <span>{viewMode === 'archive' ? 'ARCHIVE' : __APP_VERSION__}</span></h1>
        </div>
        <div className="status-section">
          <button className="icon-btn" onClick={() => setIsMuted(!isMuted)}>
            {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>

          {viewMode === 'archive' && (
            <button className="return-live-btn" onClick={returnToLive}>
              <Radio size={16} /> RETURN TO LIVE
            </button>
          )}

          {viewMode === 'live' && (
            <div className={`status-pill ${isConnected ? (tacticalHealth.status === 'DEGRADED' ? 'degraded' : 'online') : 'offline'}`}>
              <div className="pulse-dot"></div>
              {isConnected ? (
                tacticalHealth.status === 'DEGRADED'
                  ? `UPLINK DEGRADED`
                  : `LIVE INTERCEPT: ${tacticalHealth.source}`
              ) : 'RECONNECTING...'}
            </div>
          )}

          {viewMode === 'sandbox' && (
            <div className="flex gap-2">
              <button className="return-live-btn sandbox" onClick={() => { setViewMode('live'); setSandboxEvent(null); }}>
                <RotateCcw size={16} /> TERMINATE ANALYSIS
              </button>
              <div className="status-pill sandbox">
                <div className="pulse-dot"></div>
                TACTICAL SANDBOX ACTIVE
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        <MapViewer />
        <Sidebar />
      </main>

      <Analytics />

      {/* Tactical SVG Filters (v0.8.7) */}
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
