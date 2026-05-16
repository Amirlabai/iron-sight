import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TacticalContext } from './TacticalContext';
import {
  ISRAEL_CENTER, DEFAULT_ZOOM, IS_PROD, WEBSOCKET_URL, TACTICAL_API_URL,
  STRATEGIC_METADATA, TACTICAL_RED, TACTICAL_BLUE, HIGHLIGHT_RED, HIGHLIGHT_BLUE,
  SEEN_ALERTS, GLOBAL_LAST_PLAY_TIME, setGlobalLastPlayTime
} from '../utils/constants';
import { getConvexHull, getCentroid, getDistance } from '../utils/geoUtils';
import missileSound from '../assets/sounds/missile_alert.mp3';
import droneSound from '../assets/sounds/hostileAircraftIntrusion_alert.mp3';

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
        if (event.category === 'newsFlash') return;
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

// --- Tactical Map Logic ---
const calculateBestMapConfig = (events) => {
  if (!events || events.length === 0) return { center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM };

  // Collect all trajectories across all events
  const allTrajectories = events.flatMap(e => e.trajectories || []);

  if (allTrajectories.length > 0) {
    // Detect unique origins across ALL threats (normalize "North Iran" -> "Iran")
    const allOrigins = [
      ...allTrajectories.map(t => t.origin),
      ...events.flatMap(e => e.clusters || []).map(c => c.origin)
    ];

    const uniqueOrigins = new Set(
      allOrigins
        .filter(o => o && o !== 'Unknown' && o !== 'newsFlash')
        .map(o => o === 'North Iran' ? 'Iran' : o)
    );

    // Find the trajectory with the LOWEST zoom level (most "strategic"/wide)
    let bestTraj = allTrajectories[0];
    let minZoom = STRATEGIC_METADATA[bestTraj.origin]?.zoom || DEFAULT_ZOOM;

    for (const traj of allTrajectories) {
      const z = STRATEGIC_METADATA[traj.origin]?.zoom || DEFAULT_ZOOM;
      if (z < minZoom) {
        minZoom = z;
        bestTraj = traj;
      }
    }

    // Multi-origin: snap to Israel center with widest strategic view
    if (uniqueOrigins.size > 1) {
      return {
        center: ISRAEL_CENTER,
        zoom: DEFAULT_ZOOM
      };
    }

    return {
      center: [
        (bestTraj.origin_coords[0] + bestTraj.target_coords[0]) / 2,
        (bestTraj.origin_coords[1] + bestTraj.target_coords[1]) / 2
      ],
      zoom: window.innerWidth < 768 ? minZoom - 1 : minZoom
    };
  }

  // Fallback to center of first event if no trajectories but has centers (e.g. earthquakes)
  const withCenter = events.find(e => e.center);
  if (withCenter) {
    return { center: withCenter.center, zoom: withCenter.zoom_level || DEFAULT_ZOOM };
  }

  return { center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM };
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
  const [timeFrame, setTimeFrame] = useState('all');
  const [mergeTimeFrameClusters, setMergeTimeFrameClusters] = useState(false);

  useAudioEngine(liveEvents, isMuted);
  const ws = useRef(null);
  const viewModeRef = useRef(viewMode);

  useEffect(() => {
    viewModeRef.current = viewMode;
  }, [viewMode]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    ws.current = new WebSocket(WEBSOCKET_URL);
    ws.current.onopen = () => { setIsConnected(true); setLoadingProgress(p => p + 30); };
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'history_sync') {
        // Only overwrite history if no filter is active to prevent 'reverting to all' bug
        if (historyFilter === 'all' && timeFrame === 'all') {
          setHistory(data.data);
        }
        setLoadingProgress(100);
        setTimeout(() => setIsReady(true), 1500);
      } else if (data.type === 'multi_alert') {
        const events = data.events || [];
        setLiveEvents(events);

        if (viewModeRef.current === 'archive' && events.length > 0) {
          setViewMode('live');
          setActiveTab('live');
        }

        const newConfig = calculateBestMapConfig(events);
        setMapConfig(prev => {
          if (prev.center[0] === newConfig.center[0] &&
            prev.center[1] === newConfig.center[1] &&
            prev.zoom === newConfig.zoom) {
            return prev;
          }
          return newConfig;
        });
      } else if (data.type === 'reset') {
        setLiveEvents([]);
        if (viewMode === 'live') { setMapConfig({ center: ISRAEL_CENTER, zoom: DEFAULT_ZOOM }); }
      } else if (data.type === 'health_status') {
        setTacticalHealth({ status: data.status, source: data.upstream_source || 'OPERATIONAL' });
      }
    };
    ws.current.onclose = () => { setIsConnected(false); setTimeout(connect, 3000); };
  }, [historyFilter, timeFrame]);

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

  const fetchHistory = useCallback(async (category = 'all', time = 'all') => {
    try {
      const baseUrl = `${TACTICAL_API_URL}/api/history`;
      const params = new URLSearchParams();
      if (category !== 'all') params.append('category', category);
      if (time !== 'all') params.append('hours', time);
      const url = `${baseUrl}?${params.toString()}`;
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
    // Fetch history whenever filters change, regardless of isReady state
    // to ensure user-initiated filters 'get it right the first time'
    fetchHistory(historyFilter, timeFrame);
  }, [historyFilter, timeFrame, fetchHistory]);

  const selectArchive = (event) => {
    setArchiveEvent(event);
    setViewMode('archive');

    // Zoom/Center Synchronization
    const dbZoom = event.zoom_level || event.trajectories?.[0]?.zoom;
    const meta = event.trajectories?.[0] ? (STRATEGIC_METADATA[event.trajectories[0].origin] || {}) : {};

    setMapConfig({
      center: event.center || ISRAEL_CENTER,
      zoom: dbZoom || meta.zoom || 8
    });
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
    setActiveTab('live');
    setTimeFrame('all');
    setHistoryFilter('all');
    const newConfig = calculateBestMapConfig(liveEvents);
    setMapConfig(newConfig);
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
  const getRenderableEvents = () => {
    if (viewMode === 'sandbox') return sandboxEvent ? [sandboxEvent] : [];
    if (viewMode === 'archive') return archiveEvent ? [archiveEvent] : [];
    if (viewMode === 'timeframe') {
      if (!mergeTimeFrameClusters) return history;

      const eventGroups = {}; // category_origin -> [events]
      history.forEach(ev => {
        const category = ev.category || 'missiles';
        const origin = ev.trajectories?.[0]?.origin || ev.clusters?.[0]?.origin || 'unknown';
        const key = `${category}_${origin}`;
        if (!eventGroups[key]) eventGroups[key] = [];
        eventGroups[key].push(ev);
      });

      const mergedEvents = [];

      Object.entries(eventGroups).forEach(([key, events]) => {
        const [category, origin] = key.split('_');
        
        // 1. Flatten all individual clusters from all events in this group
        const allClusters = [];
        events.forEach(ev => {
          if (ev.clusters) allClusters.push(...ev.clusters);
        });

        if (allClusters.length === 0) return;

        // 2. Group clusters by proximity (35km threshold) or shared cities
        const superClusters = []; // Array of arrays of clusters
        const visited = new Set();

        for (let i = 0; i < allClusters.length; i++) {
          if (visited.has(i)) continue;

          const currentGroup = [];
          const queue = [i];
          visited.add(i);

          while (queue.length > 0) {
            const idx = queue.shift();
            const c1 = allClusters[idx];
            currentGroup.push(c1);

            for (let j = 0; j < allClusters.length; j++) {
              if (visited.has(j)) continue;
              const c2 = allClusters[j];

              // Check if c1 and c2 should merge
              let shouldMerge = false;

              // Proximity check (centroids)
              if (c1.centroid && c2.centroid) {
                const dist = getDistance(c1.centroid, c2.centroid);
                if (dist < 12) shouldMerge = true;
              }

              // Shared city check
              if (!shouldMerge && c1.cities && c2.cities) {
                const names1 = new Set(c1.cities.map(c => typeof c === 'string' ? c : c.name));
                const names2 = new Set(c2.cities.map(c => typeof c === 'string' ? c : c.name));
                for (const name of names1) {
                  if (names2.has(name)) {
                    shouldMerge = true;
                    break;
                  }
                }
              }

              if (shouldMerge) {
                visited.add(j);
                queue.push(j);
              }
            }
          }
          superClusters.push(currentGroup);
        }

        // 3. Create one "Super Event" per proximity island
        superClusters.forEach((group, sIdx) => {
          const baseEvent = JSON.parse(JSON.stringify(events[0]));
          
          // Calculate time range for the group
          const times = group.map(c => new Date(c.time || baseEvent.time).getTime());
          const minTime = new Date(Math.min(...times));
          const maxTime = new Date(Math.max(...times));
          const timeRangeStr = minTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + 
                               ' - ' + 
                               maxTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          const superEvent = {
            ...baseEvent,
            id: `merged_${key}_${sIdx}`,
            category,
            mergedCount: group.length,
            timeRange: timeRangeStr,
            all_cities: [],
            clusters: [{
              origin: origin,
              cities: [],
              hull: [],
              centroid: null
            }]
          };

          const masterCluster = superEvent.clusters[0];
          const points = [];
          const cityNames = new Set();

          group.forEach(c => {
            if (c.cities) {
              c.cities.forEach(city => {
                const name = typeof city === 'string' ? city : city.name;
                if (!cityNames.has(name)) {
                  masterCluster.cities.push(city);
                  superEvent.all_cities.push(city);
                  cityNames.add(name);
                }
                if (city.coords) points.push(city.coords);
              });
            }
            if (c.hull) points.push(...c.hull);
            if (c.centroid) points.push(c.centroid);
          });

          if (points.length > 0) {
            masterCluster.hull = getConvexHull(points);
            masterCluster.centroid = getCentroid(points);
          }

          mergedEvents.push(superEvent);
        });
      });

      return mergedEvents;
    }
    // If we are in the history tab, we should default to showing the history stream
    // unless we are explicitly in another mode (like viewing a specific archive event).
    if (activeTab === 'archive') return history;

    return liveEvents;
  };

  const renderableEvents = getRenderableEvents();



  const hasSimulation = (viewMode === 'live' ? liveEvents : renderableEvents).some(e => e.is_simulation);
  const totalClusters = renderableEvents.reduce((acc, ev) => acc + (ev.clusters?.length || 0), 0);
  const totalTargets = renderableEvents.reduce((acc, ev) => acc + (ev.clusters?.reduce((a, c) => a + (c.cities?.length || 0), 0) || 0), 0);
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
    renderableEvents, hasSimulation, totalClusters, totalTargets,    timeFrame, setTimeFrame, mergeTimeFrameClusters, setMergeTimeFrameClusters, setMapConfig,
    tacticalColor, highlightColor,
  };

  return (
    <TacticalContext.Provider value={value}>
      {children}
    </TacticalContext.Provider>
  );
}
