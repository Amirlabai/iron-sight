import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Polyline, useMap, Marker, Popup, GeoJSON, Tooltip, Polygon, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import { Activity, ShieldAlert, Navigation2, Zap, RotateCcw, History, Radio, Clock, Map as MapIcon, Volume2, VolumeX, Terminal, Shield, ChevronDown, ChevronRight } from 'lucide-react';
import TACTICAL_GEOJSON from './assets/countries.json';
import { Analytics } from '@vercel/analytics/react';
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

// --- MISSION: Tactical Geodata Decoupling ---
// Generate the legacy coordinate mapping from the new GeoJSON for component compatibility
const TACTICAL_BOUNDARIES = TACTICAL_GEOJSON.features.reduce((acc, feature) => {
  const name = feature.properties.location;
  // Flip [lon, lat] -> [lat, lon] for Leaflet Polygon component (legacy support)
  const coords = feature.geometry.coordinates[0].map(p => [p[1], p[0]]);
  acc[name] = coords;
  return acc;
}, {});

// Generate the Metadata Map (Depth/Zoom)
const STRATEGIC_METADATA = TACTICAL_GEOJSON.features.reduce((acc, feature) => {
  acc[feature.properties.location] = {
    depth: feature.properties.depth,
    zoom: feature.properties["zoom level"],
    color: feature.properties.color
  };
  return acc;
}, {});

// Mission Networking: Sanitize and construct URLs
const IS_PROD = import.meta.env.PROD;
const RAW_HOST = import.meta.env.VITE_WS_URL || window.location.host;
const WS_HOST = RAW_HOST.replace(/^https?:\/\//, '');

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const WEBSOCKET_URL = `${WS_PROTOCOL}//${WS_HOST}/ws`;
// Masking the backend URL via Vercel /api proxy in production to prevent console exposure
const TACTICAL_API_URL = IS_PROD ? "" : `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${WS_HOST}`;
const MISSION_KEY = import.meta.env.VITE_MISSION_KEY;

// Tactical Sound Effect
const PING_SOUND = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');

function MapController({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.5 });
  }, [center, zoom, map]);
  return null;
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: () => onMapClick(),
  });
  return null;
}

const TrackingDrone = ({ positions, color }) => {
  const [currentIdx, setCurrentIdx] = React.useState(0);
  const [progress, setProgress] = React.useState(0);

  React.useEffect(() => {
    if (!positions || positions.length < 2) return;
    let animationFrameId;
    let startTime = Date.now();
    const duration = 2000; // 2 seconds per segment

    const animate = () => {
      const now = Date.now();
      const elapsed = now - startTime;
      const p = Math.min(elapsed / duration, 1);
      
      setProgress(p);

      if (p >= 1) {
        startTime = Date.now();
        setCurrentIdx((prev) => (prev + 1) % positions.length);
      }
      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [positions]);

  if (!positions || positions.length === 0) return null;
  if (positions.length === 1) {
    return (
      <Marker position={positions[0]} icon={L.divIcon({
        className: 'drone-tracker-marker',
        html: `<div style="width: 0; height: 0; border-top: 6px solid transparent; border-bottom: 6px solid transparent; border-left: 14px solid ${color}; filter: drop-shadow(0 0 10px ${color});"></div>`,
        iconSize: [14, 12],
        iconAnchor: [7, 6]
      })} />
    );
  }
  
  const p1 = positions[currentIdx];
  const p2 = positions[(currentIdx + 1) % positions.length];
  
  const lat = p1[0] + (p2[0] - p1[0]) * progress;
  const lng = p1[1] + (p2[1] - p1[1]) * progress;

  const dx = p2[1] - p1[1];
  const dyScreen = -(p2[0] - p1[0]);
  const angle = Math.atan2(dyScreen, dx) * (180 / Math.PI);

  return (
    <React.Fragment>
      <Polyline positions={positions} pathOptions={{ color: color, weight: 2, dashArray: '5, 10', opacity: 0.5, className: 'trajectory-line' }} />
      <Marker position={[lat, lng]} icon={L.divIcon({
        className: 'drone-tracker-marker',
        html: `<div style="transform: rotate(${angle}deg); width: 0; height: 0; border-top: 6px solid transparent; border-bottom: 6px solid transparent; border-left: 20px solid ${color}; filter: drop-shadow(0 0 10px ${color});"></div>`,
        iconSize: [20, 12],
        iconAnchor: [10, 6]
      })} />
    </React.Fragment>
  );
};

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
  const [sandboxEvent, setSandboxEvent] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [regionalData, setRegionalData] = useState({});
  const [expandedRegions, setExpandedRegions] = useState(new Set());
  const [citySearch, setCitySearch] = useState('');
  const [sandboxInput, setSandboxInput] = useState('');
  const [tacticalHealth, setTacticalHealth] = useState({ status: 'OPERATIONAL', source: 'SYNCING...' });
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);
  const ws = useRef(null);
  const lastAlertSoundTime = useRef(0);

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
        const now = Date.now();
        if (!isMuted && now - lastAlertSoundTime.current > 20000) {
          PING_SOUND.play().catch(() => { });
          lastAlertSoundTime.current = now;
        }
        const newEvent = {
          title: data.title,
          category: data.category,
          clusters: data.clusters,
          trajectories: data.trajectories,
          highlight_origins: data.highlight_origins,
          time: data.time,
          center: data.center,
          zoom_level: data.zoom_level,
          visual_config: data.visual_config,
          is_simulation: data.is_simulation
        };
        setLiveEvent(newEvent);
        if (viewMode === 'archive') { setViewMode('live'); setActiveTab('live'); }
        if (data.center) {
          setMapConfig({
            center: data.center,
            zoom: data.zoom_level || 8
          });
        }
      } else if (data.type === 'reset') {
        setLiveEvent(null);
        if (viewMode === 'live') { setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM }); }
      } else if (data.type === 'health_status') {
        setTacticalHealth({ status: data.status, source: data.upstream_source });
      }
    };
    ws.current.onclose = () => { setIsConnected(false); setTimeout(connect, 3000); };
  }, [viewMode, isMuted]);

  useEffect(() => {
    connect();

    // Fetch regional data for Sandbox
    fetch(`${TACTICAL_API_URL}/api/cities`).then(res => res.json()).then(data => setRegionalData(data)).catch(err => { if (!IS_PROD) console.error("CITIES_FETCH_FAILED", err); });

    // Fail-Safe: Don't let the splash screen hang indefinitely on network/sync hiccups
    const missionTimer = setTimeout(() => {
      if (!isReady) {
        if (!IS_PROD) console.warn("TACTICAL_UPLINK: Transitioning to manual UI mode.");
        setIsReady(true);
      }
    }, 6000);

    return () => {
      ws.current?.close();
      clearTimeout(missionTimer);
    };
  }, [connect, isReady]);

  const selectArchive = (event) => {
    setArchiveEvent(event);
    setViewMode('archive');
    if (event.trajectories.length > 0) {
      const mainTraj = event.trajectories[0];
      const origin_coords = mainTraj.marker_coords || mainTraj.origin_coords;
      const meta = STRATEGIC_METADATA[mainTraj.origin] || {};
      setMapConfig({
        center: [(origin_coords[0] + ISRAEL_CENTER[0]) / 2, (origin_coords[1] + ISRAEL_CENTER[1]) / 2],
        zoom: meta.zoom || 8
      });
    }
  };


  const toggleCity = (city) => {
    const currentCities = sandboxInput.split(/[;\n]/).map(c => c.trim()).filter(c => c);
    if (currentCities.includes(city)) {
      setSandboxInput(currentCities.filter(c => c !== city).join('; '));
    } else {
      setSandboxInput([...currentCities, city].join('; '));
    }
  };

  const toggleRegion = (regionName, e) => {
    e.stopPropagation();
    const regionCities = Object.keys(regionalData[regionName]);
    const currentCities = sandboxInput.split(/[;\n]/).map(c => c.trim()).filter(c => c);
    const allInRegionSelected = regionCities.every(c => currentCities.includes(c));

    if (allInRegionSelected) {
      setSandboxInput(currentCities.filter(c => !regionCities.includes(c)).join('; '));
    } else {
      const uniqueNew = [...new Set([...currentCities, ...regionCities])];
      setSandboxInput(uniqueNew.join('; '));
    }
  };

  const toggleExpand = (region) => {
    const next = new Set(expandedRegions);
    if (next.has(region)) next.delete(region);
    else next.add(region);
    setExpandedRegions(next);
  };

  const returnToLive = () => {
    setViewMode('live');
    if (!liveEvent) setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM });
    else {
      const mainTraj = liveEvent.trajectories[0];
      const meta = STRATEGIC_METADATA[mainTraj.origin] || {};
      setMapConfig({
        center: [(mainTraj.origin_coords[0] + mainTraj.target_coords[0]) / 2, (mainTraj.origin_coords[1] + mainTraj.target_coords[1]) / 2],
        zoom: meta.zoom || 8
      });
    }
  };

  const runSandboxAnalysis = async () => {
    if (!sandboxInput.trim()) return;
    setIsAnalyzing(true);
    try {
      const cities = sandboxInput.split(/[;\n]/).map(c => c.trim()).filter(c => c);
      const resp = await fetch(`${TACTICAL_API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cities })
      });
      if (resp.ok) {
        const data = await resp.json();
        setSandboxEvent(data);
        setViewMode('sandbox');
        setMapConfig({
          center: data.center,
          zoom: data.zoom_level || 8
        });
      }
    } catch (err) {
      if (!IS_PROD) console.error("SANDBOX_ANALYSIS_FAILED:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };
  const currentEvent = viewMode === 'sandbox' ? sandboxEvent : (viewMode === 'live' ? liveEvent : archiveEvent);

  // Tactical Color Tokens (Mirrored in CSS variables)
  const TACTICAL_RED = '#ff4d4d';
  const TACTICAL_BLUE = '#4d94ff';
  const HIGHLIGHT_RED = '#ff0000';
  const HIGHLIGHT_BLUE = '#0066ff';

  const tacticalColor = viewMode === 'sandbox' ? TACTICAL_BLUE : TACTICAL_RED;
  const highlightColor = viewMode === 'sandbox' ? HIGHLIGHT_BLUE : HIGHLIGHT_RED;
  const dragControls = useDragControls();

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (window.innerWidth <= 1024) {
      setIsSidebarExpanded(true);
    }
  };

  return (
    <div className={`dashboard-container ${viewMode} ${isSidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
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
        <div className="map-wrapper">
          <div className="map-overlay-info">
            {viewMode === 'archive' && <div className="archive-watermark">HISTORICAL DATA REWIND | {archiveEvent?.time}</div>}
            {viewMode === 'sandbox' && <div className="sandbox-watermark">DRY RUN ANALYSIS | Hypo-Salvo</div>}
            {currentEvent?.is_simulation && viewMode === 'live' && <div className="sandbox-watermark" style={{color: '#ff9500', borderColor: '#ff9500'}}>SIMULATION EXERCISE ACTIVE</div>}
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
            <MapClickHandler onMapClick={() => { if (window.innerWidth <= 1024) setIsSidebarExpanded(false); }} />

            {/* Israel Base Layer Only (Detected origins highlighted dynamically below) */}
            <Polygon
              key="israel-base-layer"
              positions={TACTICAL_BOUNDARIES['Israel']}
              pathOptions={{
                color: STRATEGIC_METADATA['Israel']?.color || '#ffffff',
                weight: 2,
                fill: true,
                fillColor: STRATEGIC_METADATA['Israel']?.color || '#ffffff',
                fillOpacity: 0.005,
                smoothFactor: 1.0,
                className: 'israel-border-static'
              }}
            />

            {currentEvent?.clusters && currentEvent.clusters.map((cluster, idx) => {
              const clusterColor = currentEvent?.visual_config?.color || STRATEGIC_METADATA[cluster.origin]?.color || tacticalColor;
              return (
                <React.Fragment key={`cluster-group-${idx}`}>
                  {cluster.hull && cluster.hull.length > 2 ? (
                    <React.Fragment>
                      <Polygon
                        positions={cluster.hull}
                        pathOptions={{
                          color: clusterColor,
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
                          fillColor: clusterColor,
                          fillOpacity: 0.3,
                          color: clusterColor,
                          weight: 2,
                          smoothFactor: 2.0,
                          className: viewMode === 'live' ? (currentEvent?.visual_config?.movement || 'pulse-animation') : ''
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
                          color: clusterColor,
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
                          fillColor: clusterColor,
                          fillOpacity: 0.4,
                          color: clusterColor,
                          weight: 2,
                          className: viewMode === 'live' ? (currentEvent?.visual_config?.movement || 'pulse-animation') : ''
                        }}
                      />
                    </React.Fragment>
                  )}
                  {viewMode === 'live' && currentEvent?.visual_config && currentEvent.visual_config.movement !== 'linear' && (() => {
                    const movement = currentEvent.visual_config.movement;
                    if (movement === 'circular_sweep') {
                      return <TrackingDrone positions={cluster.cities.map(c => c.coords)} color={clusterColor} />;
                    }
                    return (
                      <Marker position={cluster.centroid} icon={L.divIcon({
                        className: 'tactical-visual-marker',
                        html: `<div class="visual-wrapper ${movement}" style="--threat-color: ${clusterColor}"></div>`,
                        iconSize: [80, 80],
                        iconAnchor: [40, 40]
                      })} />
                    );
                  })()}
                </React.Fragment>
              );
            })}

            {currentEvent?.trajectories && currentEvent.trajectories.map((traj, idx) => {
              const trajColor = currentEvent?.visual_config?.color || STRATEGIC_METADATA[traj.origin]?.color || tacticalColor;
              return (
                <React.Fragment key={`traj-group-${idx}`}>
                  <Polyline
                    positions={[traj.origin_coords, traj.target_coords]}
                    pathOptions={{
                      color: trajColor,
                      weight: 10,
                      opacity: 0.1,
                      smoothFactor: 2.0,
                      className: 'trajectory-halo'
                    }}
                  />
                  <Polyline
                    positions={[traj.origin_coords, traj.target_coords]}
                    pathOptions={{
                      color: trajColor,
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
                          <div class="origin-label" style="background: ${trajColor}">ORIGIN: ${traj.origin.toUpperCase()}</div>
                          <div class="origin-pin" style="background: ${trajColor}4D; box-shadow: 0 0 10px ${trajColor}"></div>
                        </div>
                      `,
                      iconSize: [100, 50],
                      iconAnchor: [50, 25]
                    })}
                  >
                    <Popup>Launch Origin: {traj.origin}</Popup>
                  </Marker>
                </React.Fragment>
              );
            })}

            {currentEvent?.highlight_origins?.map((org, idx) => (
              <React.Fragment key={`highlight-origin-${idx}`}>
                {TACTICAL_BOUNDARIES[org.name] ? (
                  <React.Fragment>
                    <Polygon
                      positions={TACTICAL_BOUNDARIES[org.name]}
                      pathOptions={{
                        color: STRATEGIC_METADATA[org.name]?.color || highlightColor,
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
                        fillColor: STRATEGIC_METADATA[org.name]?.color || highlightColor,
                        fillOpacity: 0.1,
                        color: STRATEGIC_METADATA[org.name]?.color || highlightColor,
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
                        color: highlightColor,
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
                        fillColor: highlightColor,
                        fillOpacity: 0.1,
                        color: highlightColor,
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

        <motion.aside
          className="sidebar"
          drag="y"
          dragControls={dragControls}
          dragListener={false}
          dragConstraints={{ top: 0, bottom: window.innerHeight * 0.7 - 60 }}
          dragElastic={0.1}
          animate={{
            y: window.innerWidth <= 1024
              ? (isSidebarExpanded ? 0 : window.innerHeight * 0.7 - 60)
              : 0
          }}
          onDragEnd={(e, info) => {
            if (info.offset.y > 50) setIsSidebarExpanded(false);
            else if (info.offset.y < -50) setIsSidebarExpanded(true);
          }}
          transition={{ type: "spring", damping: 30, stiffness: 350 }}
          style={{ height: window.innerWidth <= 1024 ? "70%" : "100%" }}
        >
          <div
            className="sidebar-tabs"
            onPointerDown={(e) => dragControls.start(e)}
            style={{ touchAction: 'none', cursor: 'grab' }}
          >
            <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => handleTabChange('live')}>
              <Activity size={18} /> LIVE
            </button>
            <button className={`tab-btn ${activeTab === 'archive' ? 'active' : ''}`} onClick={() => handleTabChange('archive')}>
              <History size={18} /> HISTORY
            </button>
            <button className={`tab-btn ${activeTab === 'sandbox' ? 'active' : ''}`} onClick={() => handleTabChange('sandbox')}>
              <Shield size={18} /> SANDBOX
            </button>
          </div>

          <div className="tab-content">
            <AnimatePresence mode="wait">
              {activeTab === 'live' ? (
                <motion.div key="live-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="live-panel">
                  <div className="stats-card">
                    <div className="card-header"><Navigation2 size={20} /><h2>ACTIVE THREATS</h2></div>
                    <div className="stats-grid">
                      <div className="stat-item"><span className="label">CLUSTERS</span><span className="value">{liveEvent?.clusters?.length || 0}</span></div>
                      <div className="stat-item"><span className="label">TARGETS</span><span className="value">{liveEvent?.clusters?.reduce((acc, c) => acc + (c.cities?.length || 0), 0) || 0}</span></div>
                    </div>
                  </div>
                  {!liveEvent ? (
                    <div className="empty-state"><RotateCcw size={48} color="#333" /><p>MONITORING AIRSPACE</p></div>
                  ) : (
                    <div className="alerts-list">
                      {liveEvent.clusters?.map((c, i) => {
                        const alertColor = liveEvent.visual_config?.color || '#ff944d';
                        return (
                          <motion.div key={i} initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="alert-item" style={{borderLeftColor: alertColor}}>
                            <div className="alert-marker" style={{background: alertColor, boxShadow: `0 0 10px ${alertColor}`}}></div>
                            <div className="alert-info">
                              <h3 style={{color: alertColor}}>{liveEvent.title?.toUpperCase()} | {liveEvent.time}</h3>
                              <p>{c.cities.map(ct => ct.name).join(', ')}</p>
                            </div>
                            <ShieldAlert size={16} color={alertColor} />
                          </motion.div>
                        );
                      })}
                    </div>
                  )}
                </motion.div>
              ) : activeTab === 'archive' ? (
                <motion.div key="history-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="archive-panel">
                  {history.length === 0 ? (
                    <div className="empty-state"><Clock size={48} color="#333" /><p>NO HISTORY RECORDED</p></div>
                  ) : (
                    <div className="history-list">
                      {history.map((event, i) => (
                        <div key={i} className={`history-item ${archiveEvent?.id === event.id && viewMode === 'archive' ? 'selected' : ''}`} onClick={() => selectArchive(event)}>
                          <div className="history-meta">
                            <span className="time">{event.time}</span>
                            <span className="date">{event.date}</span>
                          </div>
                          <div className="history-title text-red-500 font-bold">{event.title || 'Unknown Salvo'}</div>
                          <div className="history-preview mb-2">{event.clusters?.[0]?.cities?.slice(0, 3).map(c => c.name).join(', ') || 'Processing targets...'}...</div>
                          {archiveEvent?.id === event.id && viewMode === 'archive' && (
                            <div className="text-[10px] text-secondary-500 font-mono italic opacity-50 border-t border-red-500/20 pt-2">
                              MISSION_ID: {archiveEvent.id}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              ) : (
                <motion.div key="sandbox-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="sandbox-panel">
                  <div className="stats-card sandbox">
                    <div className="card-header"><Shield size={20} /><h2>TACTICAL SANDBOX</h2></div>
                    <p className="text-xs text-sub mb-4 italic">Hypothesize threat vectors by plotting city clusters.</p>

                    {/* Regional Selection Suite */}
                    <div className="regional-picker">
                      <div className="picker-controls">
                        <div className="search-box">
                          <Terminal size={14} />
                          <input
                            type="text"
                            placeholder="Filter regions or cities..."
                            value={citySearch}
                            onChange={(e) => setCitySearch(e.target.value)}
                          />
                        </div>
                        <div className="master-toggles">
                          <button onClick={() => setExpandedRegions(new Set(Object.keys(regionalData)))}>EXPAND ALL</button>
                          <button onClick={() => setExpandedRegions(new Set())}>COLLAPSE</button>
                        </div>
                      </div>

                      <div className="regions-container">
                        {Object.entries(regionalData)
                          .filter(([name, cities]) =>
                            name.includes(citySearch) ||
                            Object.keys(cities).some(c => c.includes(citySearch))
                          )
                          .map(([region, cities]) => {
                            const regionCities = Object.keys(cities);
                            const currentCities = sandboxInput.split(/[;\n]/).map(c => c.trim()).filter(c => c);
                            const selectedInRegion = regionCities.filter(c => currentCities.includes(c));
                            const isExpanded = expandedRegions.has(region) || citySearch.length > 0;

                            return (
                              <div key={region} className={`region-group ${isExpanded ? 'expanded' : ''}`}>
                                <div className="region-header" onClick={() => toggleExpand(region)}>
                                  <div className="region-info">
                                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                    <span className="region-name">{region}</span>
                                    <span className="count-pill">{selectedInRegion.length}/{regionCities.length}</span>
                                  </div>
                                  <button
                                    className={`select-all-btn ${selectedInRegion.length === regionCities.length ? 'all' : ''}`}
                                    onClick={(e) => toggleRegion(region, e)}
                                  >
                                    {selectedInRegion.length === regionCities.length ? 'DESELECT' : 'SELECT ALL'}
                                  </button>
                                </div>
                                {isExpanded && (
                                  <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} className="region-cities">
                                    {regionCities
                                      .filter(c => c.includes(citySearch))
                                      .map(city => (
                                        <button
                                          key={city}
                                          className={`city-pill ${currentCities.includes(city) ? 'active' : ''}`}
                                          onClick={() => toggleCity(city)}
                                        >
                                          {city}
                                        </button>
                                      ))}
                                  </motion.div>
                                )}
                              </div>
                            );
                          })}
                      </div>
                    </div>

                    <textarea
                      className="sandbox-textarea"
                      placeholder="Targets (separated by ; or New-Line)..."
                      value={sandboxInput}
                      onChange={(e) => setSandboxInput(e.target.value)}
                    />
                    <button
                      className="analyze-btn"
                      onClick={runSandboxAnalysis}
                      disabled={isAnalyzing}
                    >
                      {isAnalyzing ? 'ENGINE PROCESSING...' : 'EXECUTE ANALYSIS'}
                    </button>
                  </div>
                  {sandboxEvent && (
                    <div className="sandbox-results">
                      <div className="alert-item sandbox">
                        <div className="alert-marker sandbox"></div>
                        <div className="alert-info">
                          <h3>{sandboxEvent.title}</h3>
                          <p>Origin mapped to {sandboxEvent.trajectories?.[0]?.origin}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.aside>
      </main>
      <Analytics />
    </div>
  );
}

export default App;
