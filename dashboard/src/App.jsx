import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Polyline, useMap, Marker, Popup, GeoJSON, Tooltip, Polygon } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldAlert, Navigation2, Zap, RotateCcw, History, Radio, Clock, Map as MapIcon, Volume2, VolumeX, Terminal, Shield, ChevronDown, ChevronRight } from 'lucide-react';
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

// Mission Networking: Use relative paths for Proxy support, or environment overrides
const WS_HOST = import.meta.env.VITE_WS_URL || window.location.host;
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const API_PROTOCOL = window.location.protocol;

const WEBSOCKET_URL = `${WS_PROTOCOL}//${WS_HOST}/ws`;
const TACTICAL_API_URL = `${API_PROTOCOL}//${WS_HOST}`;
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

  useEffect(() => { 
    connect(); 
    
    // Fetch regional data for Sandbox
    fetch(`${TACTICAL_API_URL}/api/cities`).then(res => res.json()).then(data => setRegionalData(data)).catch(err => console.error("CITIES_FETCH_FAILED", err));

    // Fail-Safe: Don't let the splash screen hang indefinitely on network/sync hiccups
    const missionTimer = setTimeout(() => {
      if (!isReady) {
        console.warn("MISSION_SYNC_TIMEOUT: Entering UI manually.");
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
      const zoomMap = {
        'Gaza': 10,
        'Lebanon': 8,
        'Iran': 6,
        'North Iran': 6,
        'Yemen': 6
      };
      
      setMapConfig({
        center: [(origin_coords[0] + ISRAEL_CENTER[0]) / 2, (origin_coords[1] + ISRAEL_CENTER[1]) / 2],
        zoom: zoomMap[mainTraj.origin] || 8
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
      setMapConfig({
        center: [(mainTraj.origin_coords[0] + mainTraj.target_coords[0]) / 2, (mainTraj.origin_coords[1] + mainTraj.target_coords[1]) / 2],
        zoom: liveEvent.zoom_level || 7
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
      console.error("SANDBOX_ANALYSIS_FAILED:", err);
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
          
          {viewMode === 'archive' && (
            <button className="return-live-btn" onClick={returnToLive}>
              <Radio size={16} /> RETURN TO LIVE
            </button>
          )}

          {viewMode === 'live' && (
            <div className={`status-pill ${isConnected ? 'online' : 'offline'}`}>
              <div className="pulse-dot"></div>
              {isConnected ? 'LIVE INTERCEPT' : 'RECONNECTING...'}
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

            {/* Israel Base Layer Only (Detected origins highlighted dynamically below) */}
            <Polygon
              key="israel-base-layer"
              positions={TACTICAL_BOUNDARIES['Israel']}
              pathOptions={{
                color: '#ffffff',
                weight: 3,
                fill: true,
                fillColor: '#ffffff',
                fillOpacity: 0.005,
                smoothFactor: 1.0,
                className: 'israel-border-static'
              }}
            />

            {currentEvent?.clusters.map((cluster, idx) => (
              <React.Fragment key={`cluster-group-${idx}`}>
                {cluster.hull && cluster.hull.length > 2 ? (
                  <React.Fragment>
                    <Polygon
                      positions={cluster.hull}
                      pathOptions={{
                        color: tacticalColor,
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
                        fillColor: tacticalColor,
                        fillOpacity: 0.3,
                        color: tacticalColor,
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
                        color: tacticalColor,
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
                        fillColor: tacticalColor,
                        fillOpacity: 0.4,
                        color: tacticalColor,
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
                    color: tacticalColor,
                    weight: 10,
                    opacity: 0.1,
                    smoothFactor: 2.0,
                    className: 'trajectory-halo'
                  }}
                />
                <Polyline
                  positions={[traj.origin_coords, traj.target_coords]}
                  pathOptions={{
                    color: tacticalColor,
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
                        <div class="origin-label" style="background: ${tacticalColor}">ORIGIN: ${traj.origin.toUpperCase()}</div>
                        <div class="origin-pin" style="background: ${tacticalColor}4D; box-shadow: 0 0 10px ${tacticalColor}"></div>
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
                        color: highlightColor,
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
                        fillColor: highlightColor,
                        fillOpacity: 0.1,
                        color: highlightColor,
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

        <aside className="sidebar">
          <div className="sidebar-tabs">
            <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
              <Activity size={18} /> LIVE
            </button>
            <button className={`tab-btn ${activeTab === 'archive' ? 'active' : ''}`} onClick={() => setActiveTab('archive')}>
              <History size={18} /> HISTORY
            </button>
            <button className={`tab-btn ${activeTab === 'sandbox' ? 'active' : ''}`} onClick={() => setActiveTab('sandbox')}>
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
                      {liveEvent.clusters?.map((c, i) => (
                        <motion.div key={i} initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="alert-item">
                          <div className="alert-marker"></div>
                          <div className="alert-info">
                            <h3>{c.origin?.toUpperCase().replace('_', ' ') || `CLUSTER ${i + 1}`} | {liveEvent.time}</h3>
                            <p>{c.cities.map(ct => ct.name).join(', ')}</p>
                          </div>
                          <Zap size={16} color="#ff944d" />
                        </motion.div>
                      ))}
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
        </aside>
      </main>
    </div>
  );
}

export default App;
