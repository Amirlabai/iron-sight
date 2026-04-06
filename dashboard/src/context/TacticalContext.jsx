import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  ISRAEL_CENTER, DEFAULT_ZOOM, IS_PROD, WEBSOCKET_URL, TACTICAL_API_URL,
  STRATEGIC_METADATA, TACTICAL_RED, TACTICAL_BLUE, HIGHLIGHT_RED, HIGHLIGHT_BLUE,
  SEEN_ALERTS, GLOBAL_LAST_PLAY_TIME, setGlobalLastPlayTime
} from '../utils/constants';
import missileSound from '../assets/sounds/missile_alert.mp3';
import droneSound from '../assets/sounds/hostileAircraftIntrusion_alert.mp3';

const TacticalContext = createContext(null);

// --- Tactical Audio Engine ---
const useAudioEngine = (liveEvents, isMuted) => {
  const activeAudioRef = useRef(null);

  useEffect(() => {
    if (isMuted && activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
  }, [isMuted]);

  useEffect(() => {
    if (isMuted || !liveEvents || liveEvents.length === 0) return;

    liveEvents.forEach(event => {
      if (!SEEN_ALERTS.has(event.id)) {
        SEEN_ALERTS.add(event.id);
        const category = (event.category === 'missiles') ? 'missiles' : 'drones';
        const now = Date.now();

        if (now - GLOBAL_LAST_PLAY_TIME > 4000) {
          setGlobalLastPlayTime(now);
          const soundFile = (category === 'missiles') ? missileSound : droneSound;
          const audio = new Audio(soundFile);
          activeAudioRef.current = audio;

          if (category === 'missiles') {
            audio.play().catch(e => console.warn('Audio playback blocked:', e));
          } else {
            let playCount = 0;
            audio.addEventListener('ended', () => {
              playCount++;
              if (playCount < 2 && !isMuted) {
                audio.play().catch(e => console.warn('Audio loop blocked:', e));
              } else {
                activeAudioRef.current = null;
              }
            });
            audio.play().catch(e => console.warn('Audio playback blocked:', e));
          }
        }
      }
    });
  }, [liveEvents, isMuted]);
};

export function TacticalProvider({ children }) {
  const [liveEvents, setLiveEvents] = useState([]);
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
  const [historyFilter, setHistoryFilter] = useState('all');

  useAudioEngine(liveEvents, isMuted);
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
      } else if (data.type === 'multi_alert') {
        const events = data.events || [];
        setLiveEvents(events);

        if (viewMode === 'archive' && events.length > 0) {
          setViewMode('live');
          setActiveTab('live');
        }

        const withTrajectory = events.find(e => e.trajectories && e.trajectories.length > 0);
        const withCenter = events.find(e => e.center);
        if (withTrajectory) {
          const traj = withTrajectory.trajectories[0];
          const meta = STRATEGIC_METADATA[traj.origin] || {};
          setMapConfig({
            center: [(traj.origin_coords[0] + traj.target_coords[0]) / 2, (traj.origin_coords[1] + traj.target_coords[1]) / 2],
            zoom: meta.zoom || 8
          });
        } else if (withCenter) {
          setMapConfig({ center: withCenter.center, zoom: withCenter.zoom_level || 8 });
        }
      } else if (data.type === 'reset') {
        setLiveEvents([]);
        if (viewMode === 'live') { setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM }); }
      } else if (data.type === 'health_status') {
        setTacticalHealth({ status: data.status, source: data.upstream_source || 'OPERATIONAL' });
      }
    };
    ws.current.onclose = () => { setIsConnected(false); setTimeout(connect, 3000); };
  }, [viewMode, isMuted]);

  useEffect(() => {
    connect();
    fetch(`${TACTICAL_API_URL}/api/cities`).then(res => res.json()).then(data => setRegionalData(data)).catch(err => { if (!IS_PROD) console.error("CITIES_FETCH_FAILED", err); });

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

  const fetchHistory = useCallback(async (category = 'all') => {
    try {
      const url = category === 'all' 
        ? `${TACTICAL_API_URL}/api/history` 
        : `${TACTICAL_API_URL}/api/history?category=${category}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setHistory(Array.isArray(data) ? data : []);
      } else {
        setHistory([]);
      }

    } catch (err) {
      if (!IS_PROD) console.error("HISTORY_FETCH_FAILED", err);
    }
  }, []);

  useEffect(() => {
    if (isReady && historyFilter) {
      fetchHistory(historyFilter);
    }
  }, [historyFilter, isReady, fetchHistory]);

  const selectArchive = (event) => {
    setArchiveEvent(event);
    setViewMode('archive');
    if (event.trajectories?.length > 0) {
      const mainTraj = event.trajectories[0];
      const origin_coords = mainTraj.marker_coords || mainTraj.origin_coords;
      const meta = STRATEGIC_METADATA[mainTraj.origin] || {};
      setMapConfig({
        center: [(origin_coords?.[0] + ISRAEL_CENTER[0]) / 2, (origin_coords?.[1] + ISRAEL_CENTER[1]) / 2],
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
      setSandboxInput([...new Set([...currentCities, ...regionCities])].join('; '));
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
    if (liveEvents.length === 0) {
      setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM });
    } else {
      const first = liveEvents[0];
      if (first.trajectories && first.trajectories.length > 0) {
        const mainTraj = first.trajectories[0];
        const meta = STRATEGIC_METADATA[mainTraj.origin] || {};
        setMapConfig({
          center: [(mainTraj.origin_coords[0] + mainTraj.target_coords[0]) / 2, (mainTraj.origin_coords[1] + mainTraj.target_coords[1]) / 2],
          zoom: meta.zoom || 8
        });
      }
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
        setMapConfig({ center: data.center, zoom: data.zoom_level || 8 });
      }
    } catch (err) {
      if (!IS_PROD) console.error("SANDBOX_ANALYSIS_FAILED:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (window.innerWidth <= 1024) { setIsSidebarExpanded(true); }
  };

  // Derived State
  const renderableEvents = viewMode === 'sandbox'
    ? (sandboxEvent ? [sandboxEvent] : [])
    : viewMode === 'archive'
      ? (archiveEvent ? [archiveEvent] : [])
      : liveEvents;

  const hasSimulation = liveEvents.some(e => e.is_simulation);
  const totalClusters = liveEvents.reduce((acc, ev) => acc + (ev.clusters?.length || 0), 0);
  const totalTargets = liveEvents.reduce((acc, ev) => acc + (ev.clusters?.reduce((a, c) => a + (c.cities?.length || 0), 0) || 0), 0);
  const tacticalColor = viewMode === 'sandbox' ? TACTICAL_BLUE : TACTICAL_RED;
  const highlightColor = viewMode === 'sandbox' ? HIGHLIGHT_BLUE : HIGHLIGHT_RED;

  const value = {
    liveEvents, history, viewMode, archiveEvent, mapConfig,
    isConnected, activeTab, isReady, isMuted, loadingProgress,
    sandboxEvent, isAnalyzing, regionalData, expandedRegions,
    citySearch, sandboxInput, tacticalHealth, isSidebarExpanded, historyFilter,
    setViewMode, setActiveTab, setIsMuted, setSandboxEvent,
    setSandboxInput, setCitySearch, setIsSidebarExpanded, setExpandedRegions,
    setHistoryFilter, selectArchive, toggleCity, toggleRegion, toggleExpand,
    returnToLive, runSandboxAnalysis, handleTabChange, fetchHistory,
    renderableEvents, hasSimulation, totalClusters, totalTargets,
    tacticalColor, highlightColor,
  };

  return (
    <TacticalContext.Provider value={value}>
      {children}
    </TacticalContext.Provider>
  );
}

export function useTactical() {
  const ctx = useContext(TacticalContext);
  if (!ctx) throw new Error('useTactical must be used within TacticalProvider');
  return ctx;
}
