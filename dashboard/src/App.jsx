import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Polyline, useMap, Marker, Popup, GeoJSON, Tooltip, Polygon } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldAlert, Navigation2, Zap, RotateCcw, History, Radio, Clock, Map as MapIcon, Volume2, VolumeX, Terminal, Shield } from 'lucide-react';
import { TACTICAL_BOUNDARIES } from './tactical_geodata';
import './App.css';

// Fix Leaflet icon issue
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const ISRAEL_CENTER = [31.7683, 35.2137];
const DEFAULT_ZOOM = 8;
const WS_HOST = import.meta.env.VITE_WS_URL || `${window.location.hostname}:8080`;
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WEBSOCKET_URL = `${WS_PROTOCOL}//${WS_HOST}/ws`;

// Tactical Sound Effect
const PING_SOUND = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');

function MapController({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.5 });
  }, [center, zoom, map]);
  return null;
}

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

function App() {
  const [liveEvent, setLiveEvent] = useState(null);
  const [history, setHistory] = useState([]);
  const [viewMode, setViewMode] = useState('live');
  const [archiveEvent, setArchiveEvent] = useState(null);
  const [mapConfig, setMapConfig] = useState({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM });
  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('live');
  const [isReady, setIsReady] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const ws = useRef(null);

  const connect = useCallback(() => {
    ws.current = new WebSocket(WEBSOCKET_URL);
    ws.current.onopen = () => { setIsConnected(true); setLoadingProgress(p => p + 30); };
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'history_sync') {
        setHistory(data.data);
        setLoadingProgress(100);
        setTimeout(() => setIsReady(true), 1500);
      } else if (data.type === 'alert') {
        if (!isMuted) PING_SOUND.play().catch(() => { });
        const newEvent = { clusters: data.clusters, trajectories: data.trajectories, time: data.time, zoom_level: data.zoom_level };
        setLiveEvent(newEvent);
        if (viewMode === 'archive') { setViewMode('live'); setActiveTab('live'); }
        if (data.trajectories.length > 0) {
          const mainTraj = data.trajectories[0];
          const origin_coords = mainTraj.marker_coords || mainTraj.origin_coords;
          setMapConfig({
            center: [(origin_coords[0] + ISRAEL_CENTER[0]) / 2, (origin_coords[1] + ISRAEL_CENTER[1]) / 2],
            zoom: data.zoom_level || 8
          });
        }
      } else if (data.type === 'reset') {
        setLiveEvent(null);
        if (viewMode === 'live') { setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM }); }
      }
    };
    ws.current.onclose = () => { setIsConnected(false); setTimeout(connect, 3000); };
  }, [viewMode, isMuted]);

  useEffect(() => { connect(); return () => ws.current?.close(); }, [connect]);

  const selectArchive = (event) => {
    setArchiveEvent(event);
    setViewMode('archive');
    if (event.trajectories.length > 0) {
      const mainTraj = event.trajectories[0];
      const origin_coords = mainTraj.marker_coords || mainTraj.origin_coords;
      const isLongRange = ["Iran", "Yemen"].includes(mainTraj.origin);
      setMapConfig({
        center: [(origin_coords[0] + ISRAEL_CENTER[0]) / 2, (origin_coords[1] + ISRAEL_CENTER[1]) / 2],
        zoom: isLongRange ? 6 : 10
      });
    }
  };

  const returnToLive = () => {
    setViewMode('live');
    if (!liveEvent) setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM });
    else {
      const mainTraj = liveEvent.trajectories[0];
      setMapConfig({
        center: [(mainTraj.origin_coords[0] + mainTraj.target_coords[0]) / 2, (mainTraj.origin_coords[1] + mainTraj.target_coords[1]) / 2],
        zoom: liveEvent.zoom_level || 7
      });
    }
  };

  const currentEvent = viewMode === 'live' ? liveEvent : archiveEvent;

  return (
    <div className={`dashboard-container ${viewMode}`}>
      <AnimatePresence>
        {!isReady && <SplashScreen progress={loadingProgress} />}
      </AnimatePresence>

      <header className="premium-header">
        <div className="logo-section">
          <img src="/favicon.png" className={`logo-img ${liveEvent ? 'alert-pulse' : ''}`} alt="IRON SIGHT" />
          <h1>IRON SIGHT <span>{viewMode === 'archive' ? 'ARCHIVE' : __APP_VERSION__}</span></h1>
        </div>
        <div className="status-section">
          <button className="icon-btn" onClick={() => setIsMuted(!isMuted)}>
            {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>
          {viewMode === 'archive' ? (
            <button className="return-live-btn" onClick={returnToLive}>
              <Radio size={16} /> RETURN TO LIVE
            </button>
          ) : (
            <div className={`status-pill ${isConnected ? 'online' : 'offline'}`}>
              <div className="pulse-dot"></div>
              {isConnected ? 'LIVE INTERCEPT' : 'RECONNECTING...'}
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        <div className="map-wrapper">
          <div className="map-overlay-info">
            {viewMode === 'archive' && <div className="archive-watermark">HISTORICAL DATA REWIND | {archiveEvent?.time}</div>}
          </div>
          <MapContainer
            center={ISRAEL_CENTER}
            zoom={DEFAULT_ZOOM}
            className="leaflet-container"
            zoomControl={false}
            preferCanvas={true}
          >
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
            <MapController center={mapConfig.center} zoom={mapConfig.zoom} />

            {/* Full Tactical Boundary Suite (Permanent Persistence) */}
            {Object.entries(TACTICAL_BOUNDARIES).map(([name, coords]) => (
              <Polygon
                key={`boundary-standby-${name}`}
                positions={coords}
                pathOptions={{
                  color: name === 'Israel' ? '#ffffff' : 'rgba(255, 255, 255, 0.2)',
                  weight: name === 'Israel' ? 3 : 1,
                  fill: true,
                  fillColor: name === 'Israel' ? '#ffffff' : '#ff0000',
                  fillOpacity: name === 'Israel' ? 0.005 : 0.01,
                  smoothFactor: 1.0,
                  className: name === 'Israel' ? 'israel-border-static' : 'standby-border'
                }}
              />
            ))}

            {currentEvent?.clusters.map((cluster, idx) => (
              <React.Fragment key={`cluster-group-${idx}`}>
                {cluster.hull && cluster.hull.length > 2 ? (
                  <React.Fragment>
                    <Polygon
                      positions={cluster.hull}
                      pathOptions={{
                        color: '#ff4d4d',
                        weight: 12,
                        opacity: 0.1,
                        fill: false,
                        smoothFactor: 2.0,
                        className: 'origin-threat-halo'
                      }}
                    />
                    <Polygon
                      positions={cluster.hull}
                      pathOptions={{
                        fillColor: '#ff4d4d',
                        fillOpacity: 0.3,
                        color: '#ff4d4d',
                        weight: 2,
                        smoothFactor: 2.0,
                        className: viewMode === 'live' ? 'pulse-animation' : ''
                      }}
                    >
                      <Tooltip sticky>Threat Area: {cluster.cities.length} Targets</Tooltip>
                    </Polygon>
                  </React.Fragment>
                ) : (
                  <React.Fragment>
                    <Circle
                      center={cluster.centroid}
                      radius={2000}
                      pathOptions={{
                        color: '#ff4d4d',
                        weight: 12,
                        opacity: 0.1,
                        fill: false,
                        className: 'origin-threat-halo'
                      }}
                    />
                    <Circle
                      center={cluster.centroid}
                      radius={2000}
                      pathOptions={{
                        fillColor: '#ff4d4d',
                        fillOpacity: 0.4,
                        color: '#ff4d4d',
                        weight: 2,
                        className: viewMode === 'live' ? 'pulse-animation' : ''
                      }}
                    />
                  </React.Fragment>
                )}
              </React.Fragment>
            ))}

            {currentEvent?.trajectories.map((traj, idx) => (
              <React.Fragment key={`traj-group-${idx}`}>
                <Polyline
                  positions={[traj.origin_coords, traj.target_coords]}
                  pathOptions={{
                    color: '#ff4d4d',
                    weight: 10,
                    opacity: 0.1,
                    smoothFactor: 2.0,
                    className: 'trajectory-halo'
                  }}
                />
                <Polyline
                  positions={[traj.origin_coords, traj.target_coords]}
                  pathOptions={{
                    color: '#ff4d4d',
                    weight: 2,
                    dashArray: '10, 10',
                    smoothFactor: 2.0,
                    className: 'trajectory-line'
                  }}
                />
                <Marker
                  position={traj.marker_coords || traj.origin_coords}
                  icon={L.divIcon({
                    className: 'custom-origin-marker',
                    html: `
                      <div class="origin-wrapper">
                        <div class="origin-label">ORIGIN: ${traj.origin.toUpperCase()}</div>
                        <div class="origin-pin"></div>
                      </div>
                    `,
                    iconSize: [100, 50],
                    iconAnchor: [50, 25]
                  })}
                >
                  <Popup>Launch Origin: {traj.origin}</Popup>
                </Marker>
              </React.Fragment>
            ))}

            {currentEvent?.highlight_origins?.map((org, idx) => (
              <React.Fragment key={`highlight-origin-${idx}`}>
                {TACTICAL_BOUNDARIES[org.name] ? (
                  <React.Fragment>
                    <Polygon
                      positions={TACTICAL_BOUNDARIES[org.name]}
                      pathOptions={{
                        color: '#ff0000',
                        weight: 15,
                        opacity: 0.05,
                        fill: false,
                        smoothFactor: 2.0,
                        className: 'origin-threat-halo'
                      }}
                    />
                    <Polygon
                      positions={TACTICAL_BOUNDARIES[org.name]}
                      pathOptions={{
                        fillColor: '#ff0000',
                        fillOpacity: 0.1,
                        color: '#ff0000',
                        weight: 1,
                        smoothFactor: 2.0,
                        className: 'origin-threat-glow'
                      }}
                    />
                  </React.Fragment>
                ) : (
                  <React.Fragment>
                    <Circle
                      center={org.coords}
                      radius={40000}
                      pathOptions={{
                        color: '#ff0000',
                        weight: 20,
                        opacity: 0.05,
                        fill: false,
                        className: 'origin-threat-halo'
                      }}
                    />
                    <Circle
                      center={org.coords}
                      radius={40000}
                      pathOptions={{
                        fillColor: '#ff0000',
                        fillOpacity: 0.1,
                        color: '#ff0000',
                        weight: 1,
                        className: 'origin-threat-glow'
                      }}
                    />
                  </React.Fragment>
                )}
              </React.Fragment>
            ))}
          </MapContainer>
        </div>

        <aside className="sidebar">
          <div className="sidebar-tabs">
            <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
              <Activity size={18} /> LIVE
            </button>
            <button className={`tab-btn ${activeTab === 'archive' ? 'active' : ''}`} onClick={() => setActiveTab('archive')}>
              <History size={18} /> HISTORY
            </button>
          </div>

          <div className="tab-content">
            <AnimatePresence mode="wait">
              {activeTab === 'live' ? (
                <motion.div key="live-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="live-panel">
                  <div className="stats-card">
                    <div className="card-header"><Navigation2 size={20} /><h2>ACTIVE THREATS</h2></div>
                    <div className="stats-grid">
                      <div className="stat-item"><span className="label">CLUSTERS</span><span className="value">{liveEvent?.clusters.length || 0}</span></div>
                      <div className="stat-item"><span className="label">TARGETS</span><span className="value">{liveEvent?.clusters.reduce((acc, c) => acc + c.cities.length, 0) || 0}</span></div>
                    </div>
                  </div>
                  {!liveEvent ? (
                    <div className="empty-state"><RotateCcw size={48} color="#333" /><p>MONITORING AIRSPACE</p></div>
                  ) : (
                    <div className="alerts-list">
                      {liveEvent.clusters.map((c, i) => (
                        <motion.div key={i} initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="alert-item">
                          <div className="alert-marker"></div>
                          <div className="alert-info">
                            <h3>CLUSTER {i + 1} | {liveEvent.time}</h3>
                            <p>{c.cities.map(ct => ct.name).join(', ')}</p>
                          </div>
                          <Zap size={16} color="#ff944d" />
                        </motion.div>
                      ))}
                    </div>
                  )}
                </motion.div>
              ) : (
                <motion.div key="history-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="archive-panel">
                  {history.length === 0 ? (
                    <div className="empty-state"><Clock size={48} color="#333" /><p>NO HISTORY RECORDED</p></div>
                  ) : (
                    <div className="history-list">
                      {history.map((event, i) => (
                        <div key={i} className={`history-item ${archiveEvent?.id === event.id && viewMode === 'archive' ? 'selected' : ''}`} onClick={() => selectArchive(event)}>
                          <div className="history-meta"><span className="time">{event.time}</span><span className="count">{event.clusters.length} CLUSTERS</span></div>
                          <div className="history-preview">{event.clusters[0].cities.slice(0, 3).map(c => c.name).join(', ')}...</div>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
