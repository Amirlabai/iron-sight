import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { TacticalContext } from './TacticalContext';
import {
  ISRAEL_CENTER, getDefaultZoom, IS_PROD, WEBSOCKET_URL, TACTICAL_API_URL,
  TACTICAL_RED, TACTICAL_BLUE, HIGHLIGHT_RED, HIGHLIGHT_BLUE,
  SEEN_ALERTS, GLOBAL_LAST_PLAY_TIME, setGlobalLastPlayTime
} from '../utils/constants';
import {
  calculateArchiveMapConfig,
  calculateTimeframeMapConfig,
} from '../utils/mapGeometry';
import { resolveMapConfig, getEventOrigin } from '../utils/mapZoomPresets';
import { filterArchiveHistory, filterHistoryByOrigin, mergeHistoryById } from '../utils/historyFilters';
import { getConvexHull, getCentroid, getDistance } from '../utils/geoUtils';
import missileSound from '../assets/sounds/missile_alert.mp3';
import droneSound from '../assets/sounds/hostileAircraftIntrusion_alert.mp3';
import { filterEventsByScope, matchesAlertScope, buildAlertNotifyKey } from '../utils/alertMatching';
import { useAlertPreferences } from '../hooks/useAlertPreferences';
import { useThemeMode } from '../hooks/useThemeMode';
import { agentDebugBurst, agentDebugLog, WS_MESSAGE_BURST } from '../utils/agentDebugLog';
import { hasSessionBooted, markSessionBooted } from '../utils/sessionBoot';
import { consumeWsReconnectDelayMs, resetWsFailStreak } from '../utils/wsReconnect';
import { lruAdd, clearLruSet } from '../utils/lruSet';
import { sortEventsByLatestFirst } from '../utils/formatters';

const HISTORY_PAGE_SIZE = 50;
const MAX_ORIGIN_AUTO_PAGES = 4;

// --- Tactical Audio Engine ---
const useAudioEngine = (liveEvents, isMuted, alertPrefs) => {
  const activeAudioRef = useRef(null);

  useEffect(() => {
    if (isMuted && activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
  }, [isMuted]);

  useEffect(() => {
    if (isMuted || !liveEvents || liveEvents.length === 0) return;

    const scoped = filterEventsByScope(liveEvents, alertPrefs?.location, {
      scope: alertPrefs?.scope || 'all',
      radiusKm: alertPrefs?.radiusKm,
    });

    scoped.forEach(event => {
      if (lruAdd(SEEN_ALERTS, event.id)) {
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
  }, [liveEvents, isMuted, alertPrefs]);
};

const NOTIFIED_KEYS = new Set();

function useScopedNotifications(liveEvents, alertPrefs) {
  useEffect(() => {
    if (!liveEvents?.length) return;
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return;

    liveEvents.forEach((event) => {
      if (event.category === 'newsFlash') return;
      const key = buildAlertNotifyKey(event);
      if (!lruAdd(NOTIFIED_KEYS, key)) return;

      const match = matchesAlertScope(alertPrefs?.location, event, {
        scope: alertPrefs?.scope || 'all',
        radiusKm: alertPrefs?.radiusKm,
      });
      if (!match) return;
      const cities = (event.all_cities || []).slice(0, 3).map((c) => (typeof c === 'object' ? c.name : c)).filter(Boolean);
      const body = cities.length ? cities.join(', ') : 'Active threat detected';

      if (document.hidden) {
        new Notification(`IRON SIGHT — ${event.title || 'Alert'}`, {
          body,
          icon: '/icon-192.png',
          tag: event.id,
        });
      }
    });
  }, [liveEvents, alertPrefs]);
}

export function TacticalProvider({ children }) {
  const [liveEvents, setLiveEvents] = useState([]);
  const [history, setHistory] = useState([]);
  const [viewMode, setViewMode] = useState('live');
  const [archiveEvent, setArchiveEvent] = useState(null);
  const [mapConfig, setMapConfig] = useState({
    center: ISRAEL_CENTER,
    zoom: getDefaultZoom(),
    bounds: null,
    maxZoom: undefined,
  });
  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('live');
  const [isReady, setIsReady] = useState(() => hasSessionBooted());
  const [isMuted, setIsMuted] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(() => (hasSessionBooted() ? 100 : 0));
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
  const [originFilter, setOriginFilter] = useState('all');
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyLoadingMore, setHistoryLoadingMore] = useState(false);
  const [mergeTimeFrameClusters, setMergeTimeFrameClusters] = useState(false);
  const [mapAutoFollowToken, setMapAutoFollowToken] = useState(0);

  const alertPrefsApi = useAlertPreferences();
  const { prefs: alertPrefs } = alertPrefsApi;
  const { themeMode, isLightMode, toggleThemeMode } = useThemeMode();
  const alertPrefsRef = useRef(alertPrefs);

  useEffect(() => {
    alertPrefsRef.current = alertPrefs;
  }, [alertPrefs]);

  useAudioEngine(liveEvents, isMuted, alertPrefs);
  useScopedNotifications(liveEvents, alertPrefs);
  const ws = useRef(null);
  const wsConnectingRef = useRef(false);
  const wsReconnectTimerRef = useRef(null);
  const historyFilterRef = useRef(historyFilter);
  const timeFrameRef = useRef(timeFrame);
  const originFilterRef = useRef(originFilter);
  const originAutoLoadRef = useRef(0);
  const historyOffsetRef = useRef(historyOffset);
  const viewModeRef = useRef(viewMode);
  const isReadyRef = useRef(isReady);

  useEffect(() => {
    viewModeRef.current = viewMode;
  }, [viewMode]);

  useEffect(() => {
    historyFilterRef.current = historyFilter;
  }, [historyFilter]);

  useEffect(() => {
    timeFrameRef.current = timeFrame;
  }, [timeFrame]);

  useEffect(() => {
    originFilterRef.current = originFilter;
  }, [originFilter]);

  useEffect(() => {
    originAutoLoadRef.current = 0;
  }, [historyFilter, timeFrame, originFilter]);

  useEffect(() => {
    historyOffsetRef.current = historyOffset;
  }, [historyOffset]);

  useEffect(() => {
    isReadyRef.current = isReady;
    if (isReady) markSessionBooted();
  }, [isReady]);

  useEffect(() => {
    let disposed = false;

    const scheduleReconnect = () => {
      if (disposed || wsReconnectTimerRef.current) return;
      const delayMs = consumeWsReconnectDelayMs();
      if (!IS_PROD) {
        console.warn(`TACTICAL_UPLINK: reconnect in ${Math.round(delayMs / 1000)}s`);
      }
      wsReconnectTimerRef.current = setTimeout(() => {
        wsReconnectTimerRef.current = null;
        openSocket();
      }, delayMs);
    };

    const openSocket = () => {
      if (disposed) return;
      if (wsConnectingRef.current) return;
      const state = ws.current?.readyState;
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;

      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current);
        wsReconnectTimerRef.current = null;
      }

      if (ws.current) {
        ws.current.onclose = null;
        ws.current.onerror = null;
        ws.current.close();
        ws.current = null;
      }

      wsConnectingRef.current = true;
      const socket = new WebSocket(WEBSOCKET_URL);
      ws.current = socket;

      socket.onopen = () => {
        if (disposed) return;
        wsConnectingRef.current = false;
        resetWsFailStreak();
        setIsConnected(true);
        setLoadingProgress((p) => p + 30);
      };

      socket.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          if (!IS_PROD) console.warn('WS_MESSAGE_PARSE_FAILED', event.data);
          return;
        }
        agentDebugBurst(
          'ws-message',
          'TacticalProvider.jsx:onmessage',
          'websocket message burst',
          { type: data.type },
          'E',
          WS_MESSAGE_BURST.threshold,
          WS_MESSAGE_BURST.windowMs,
        );
        if (data.type === 'multi_alert') {
          agentDebugLog(
            'TacticalProvider.jsx:multi_alert',
            'multi_alert received',
            { eventCount: (data.events || []).length },
            'E',
          );
        }
        if (data.type === 'history_sync') {
          if (historyFilterRef.current === 'all' && timeFrameRef.current === 'all') {
            setHistory(filterArchiveHistory(data.data));
          }
          setLoadingProgress(100);
          setIsReady(true);
        } else if (data.type === 'multi_alert') {
          const events = sortEventsByLatestFirst(data.events || []);
          setLiveEvents(events);

          const newConfig = resolveMapConfig(events, alertPrefsRef.current);
          setMapConfig((prev) => {
            if (
              prev.center[0] === newConfig.center[0] &&
              prev.center[1] === newConfig.center[1] &&
              prev.zoom === newConfig.zoom
            ) {
              return prev;
            }
            return newConfig;
          });
        } else if (data.type === 'reset') {
          setLiveEvents([]);
          clearLruSet(SEEN_ALERTS);
          clearLruSet(NOTIFIED_KEYS);
          if (viewModeRef.current === 'live') {
            setMapConfig({
              center: ISRAEL_CENTER,
              zoom: getDefaultZoom(),
              bounds: null,
              maxZoom: undefined,
            });
          }
        } else if (data.type === 'health_status') {
          setTacticalHealth({
            status: data.status,
            source: data.upstream_source || 'OPERATIONAL',
          });
        }
      };

      socket.onclose = () => {
        if (disposed) return;
        wsConnectingRef.current = false;
        if (ws.current === socket) ws.current = null;
        setIsConnected(false);
        scheduleReconnect();
      };

      socket.onerror = () => {
        /* onclose follows */
      };
    };

    openSocket();
    fetch(`${TACTICAL_API_URL}/api/cities`)
      .then((res) => res.json())
      .then((data) => setRegionalData(data))
      .catch((err) => {
        if (!IS_PROD) console.error('CITIES_FETCH_FAILED', err);
      });

    return () => {
      disposed = true;
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current);
        wsReconnectTimerRef.current = null;
      }
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.onerror = null;
        ws.current.close();
        ws.current = null;
      }
      wsConnectingRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (isReadyRef.current) return undefined;
    const bootTimer = setTimeout(() => {
      if (!isReadyRef.current) {
        if (!IS_PROD) console.warn('TACTICAL_UPLINK: Transitioning to manual UI mode.');
        setIsReady(true);
        setLoadingProgress(100);
      }
    }, 4000);
    return () => clearTimeout(bootTimer);
  }, []);

  const fetchHistory = useCallback(async (
    category = 'all',
    time = 'all',
    options = {},
  ) => {
    const {
      append = false,
      offset = 0,
      limit = HISTORY_PAGE_SIZE,
    } = options;
    try {
      if (append) {
        setHistoryLoadingMore(true);
      }
      const baseUrl = `${TACTICAL_API_URL}/api/history`;
      const params = new URLSearchParams();
      if (category !== 'all') params.append('category', category);
      if (time !== 'all') params.append('hours', time);
      params.append('limit', String(limit));
      params.append('offset', String(offset));
      const url = `${baseUrl}?${params.toString()}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const raw = Array.isArray(data) ? data : [];
        const rows = filterArchiveHistory(raw);
        if (append) {
          setHistory((prev) => mergeHistoryById(prev, rows));
        } else {
          setHistory(rows);
        }
        const nextOffset = offset + raw.length;
        setHistoryOffset(nextOffset);
        setHistoryHasMore(raw.length === limit);
      } else {
        if (!append) {
          setHistory([]);
          setHistoryOffset(0);
        }
        setHistoryHasMore(false);
      }

      if (viewModeRef.current === 'timeframe') {
        setMapConfig(calculateTimeframeMapConfig());
      }
    } catch (err) {
      if (!IS_PROD) console.error("HISTORY_FETCH_FAILED", err);
      if (!append) {
        setHistoryHasMore(false);
      }
    } finally {
      if (append) {
        setHistoryLoadingMore(false);
      }
    }
  }, []);

  const loadMoreHistory = useCallback(() => {
    if (historyLoadingMore || !historyHasMore) return;
    fetchHistory(historyFilterRef.current, timeFrameRef.current, {
      append: true,
      offset: historyOffsetRef.current,
      limit: HISTORY_PAGE_SIZE,
    });
  }, [fetchHistory, historyHasMore, historyLoadingMore]);

  useEffect(() => {
    // Fetch history whenever filters change, regardless of isReady state
    // to ensure user-initiated filters 'get it right the first time'
    fetchHistory(historyFilter, timeFrame, { append: false, offset: 0, limit: HISTORY_PAGE_SIZE });
  }, [historyFilter, timeFrame, fetchHistory]);

  const selectArchive = (event) => {
    setArchiveEvent(event);
    setViewMode('archive');
    setMapConfig(calculateArchiveMapConfig(event));
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
    setOriginFilter('all');
    setMapConfig(resolveMapConfig(liveEvents, alertPrefsRef.current));
    setMapAutoFollowToken((t) => t + 1);
  };

  useEffect(() => {
    if (viewMode !== 'live') return;
    setMapConfig(resolveMapConfig(liveEvents, alertPrefs));
  }, [alertPrefs.mapZoomLevels, liveEvents, viewMode]);

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
          zoom: data.zoom_level || 8,
          bounds: null,
          maxZoom: undefined,
        });
      }
    } catch (err) {
      if (!IS_PROD) console.error("SANDBOX_ANALYSIS_FAILED:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const filteredHistory = useMemo(
    () => filterHistoryByOrigin(filterArchiveHistory(history), originFilter),
    [history, originFilter],
  );

  useEffect(() => {
    if (activeTab !== 'archive' || originFilter === 'all') return;
    if (historyLoadingMore || !historyHasMore) return;
    if (filteredHistory.length > 0) return;
    if (originAutoLoadRef.current >= MAX_ORIGIN_AUTO_PAGES) return;
    originAutoLoadRef.current += 1;
    loadMoreHistory();
  }, [
    activeTab,
    originFilter,
    filteredHistory.length,
    historyHasMore,
    historyLoadingMore,
    loadMoreHistory,
  ]);

  useEffect(() => {
    if (!archiveEvent || originFilter === 'all') return;
    if (getEventOrigin(archiveEvent) !== originFilter) {
      setArchiveEvent(null);
    }
  }, [originFilter, archiveEvent]);

  const renderableEvents = useMemo(() => {
    if (viewMode === 'sandbox') return sandboxEvent ? [sandboxEvent] : [];
    if (viewMode === 'archive') return archiveEvent ? [archiveEvent] : [];
    if (viewMode === 'timeframe') {
      if (!mergeTimeFrameClusters) return filteredHistory;

      const eventGroups = {}; // category_origin -> [events]
      filteredHistory.forEach(ev => {
        const category = ev.category || 'missiles';
        const origin = ev.trajectories?.[0]?.origin || ev.clusters?.[0]?.origin || 'unknown';
        const key = `${category}_${origin}`;
        if (!eventGroups[key]) eventGroups[key] = [];
        eventGroups[key].push(ev);
      });

      const mergedEvents = [];

      Object.entries(eventGroups).forEach(([key, events]) => {
        const sep = key.indexOf('_');
        const category = key.slice(0, sep);
        const origin = key.slice(sep + 1);
        
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
                if (dist < 8) shouldMerge = true;
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

          const trajSample = events
            .flatMap(e => e.trajectories || [])
            .find(t => t.origin === origin);
          if (trajSample) {
            superEvent.trajectories = [trajSample];
          } else {
            const memberEntries = events
              .flatMap(e => e.trajectories || [])
              .filter(t => t.origin === origin && t.origin_coords?.length >= 2);
            if (memberEntries.length > 0) {
              const avgLat = memberEntries.reduce((s, t) => s + t.origin_coords[0], 0) / memberEntries.length;
              const avgLng = memberEntries.reduce((s, t) => s + t.origin_coords[1], 0) / memberEntries.length;
              const avg = [avgLat, avgLng];
              superEvent.trajectories = [{
                origin,
                origin_coords: avg,
                marker_coords: avg,
              }];
            }
          }

          mergedEvents.push(superEvent);
        });
      });

      return mergedEvents;
    }
    return liveEvents;
  }, [viewMode, liveEvents, filteredHistory, archiveEvent, sandboxEvent, mergeTimeFrameClusters]);

  // Sidebar Logic: Show history stream in sidebar even if viewMode is 'live',
  // but keep the map clean unless a specific event/timeframe is selected.
  const sidebarEvents =
    activeTab === 'archive' && (viewMode === 'live' || viewMode === 'archive')
      ? filteredHistory
      : renderableEvents;

  const hasSimulation = (viewMode === 'live' ? liveEvents : renderableEvents).some(e => e.is_simulation);
  const totalClusters = sidebarEvents.reduce((acc, ev) => acc + (ev.clusters?.length || 0), 0);
  const totalTargets = sidebarEvents.reduce((acc, ev) => acc + (ev.clusters?.reduce((a, c) => a + (c.cities?.length || 0), 0) || 0), 0);
  const tacticalColor = viewMode === 'sandbox' ? TACTICAL_BLUE : TACTICAL_RED;
  const highlightColor = viewMode === 'sandbox' ? HIGHLIGHT_BLUE : HIGHLIGHT_RED;

  const originFilterLoading = activeTab === 'archive'
    && originFilter !== 'all'
    && filteredHistory.length === 0
    && historyHasMore;

  const value = {
    liveEvents, history, viewMode, archiveEvent, mapConfig,
    isConnected, activeTab, isReady, isMuted, loadingProgress,
    sandboxEvent, isAnalyzing, regionalData, expandedRegions,
    citySearch, sandboxInput, tacticalHealth, isSidebarExpanded, historyFilter,
    setViewMode, setActiveTab, setIsMuted, setSandboxEvent,
    setSandboxInput, setCitySearch, setIsSidebarExpanded, setExpandedRegions,
    setHistoryFilter, originFilter, setOriginFilter, filteredHistory, originFilterLoading,
    selectArchive, toggleCity, toggleRegion, toggleExpand,
    returnToLive, runSandboxAnalysis, handleTabChange, fetchHistory,
    renderableEvents, sidebarEvents, hasSimulation, totalClusters, totalTargets,
    timeFrame, setTimeFrame, mergeTimeFrameClusters, setMergeTimeFrameClusters, setMapConfig,
    historyOffset, historyHasMore, historyLoadingMore, loadMoreHistory,
    mapAutoFollowToken,
    tacticalColor, highlightColor,
    alertPrefs,
    alertPrefsApi,
    themeMode,
    isLightMode,
    toggleThemeMode,
  };

  return (
    <TacticalContext.Provider value={value}>
      {children}
    </TacticalContext.Provider>
  );
}
