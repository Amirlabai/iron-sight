// Mobile bottom sheet: .context/MOBILE_SHELL_SPEC.md (peek = drag zone only, useMotionValue Y).
import React from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, animate } from 'framer-motion';
import {
  Activity, ShieldAlert, Navigation2, RotateCcw, History,
  Clock, Shield, ChevronDown, ChevronRight, Terminal,
  Rocket, Plane, Zap, Wind, Users, Waves
} from 'lucide-react';
import { useTactical } from '../../context/TacticalContext';
import { formatTime, formatDateTime, dateToDisplay, displayToDate } from '../../utils/formatters';
import {
  CATEGORY_COLORS,
  categoryTint,
  MOBILE_LAYOUT_BREAKPOINT,
  MOBILE_SIDEBAR_HEIGHT_RATIO,
  MOBILE_SIDEBAR_PEEK_PX,
} from '../../utils/constants';
import { calculateTimeframeMapConfig } from '../../utils/mapGeometry';
import { agentDebugBurst, agentDebugLog } from '../../utils/agentDebugLog';

export default function Sidebar() {
  const {
    activeTab, handleTabChange, liveEvents, history,
    viewMode, archiveEvent, selectArchive,
    sandboxEvent, sandboxInput, setSandboxInput,
    citySearch, setCitySearch, regionalData,
    expandedRegions, isAnalyzing, isSidebarExpanded,
    setIsSidebarExpanded, toggleCity, toggleRegion,
    toggleExpand, runSandboxAnalysis,
    totalClusters, totalTargets, setExpandedRegions,

    historyFilter, setHistoryFilter, fetchHistory,
    timeFrame, setTimeFrame, mergeTimeFrameClusters, setMergeTimeFrameClusters, setViewMode, setMapConfig,
    renderableEvents, sidebarEvents
  } = useTactical();

  const [expandedId, setExpandedId] = React.useState(null);
  const seenLiveAlertIds = React.useRef(new Set());

  React.useEffect(() => {
    setExpandedId(null);
  }, [historyFilter]);

  const dragControls = useDragControls();
  const sheetY = useMotionValue(0);

  const [viewport, setViewport] = React.useState(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
  }));

  React.useEffect(() => {
    const onResize = () => {
      // #region agent log
      agentDebugBurst(
        'sidebar-viewport-resize',
        'Sidebar.jsx:onResize',
        'viewport resize burst',
        { w: window.innerWidth, h: window.innerHeight },
        'F',
      );
      // #endregion
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    const vv = window.visualViewport;
    const onVisualViewport = () => {
      const w = Math.round(vv?.width ?? window.innerWidth);
      const h = Math.round(vv?.height ?? window.innerHeight);
      setViewport((prev) => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
      // #region agent log
      agentDebugBurst(
        'visual-viewport',
        'Sidebar.jsx:visualViewport',
        'visualViewport resize burst',
        { w, h, innerH: window.innerHeight },
        'F',
      );
      // #endregion
    };
    vv?.addEventListener('resize', onVisualViewport);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
      vv?.removeEventListener('resize', onVisualViewport);
    };
  }, []);

  const isMobile = viewport.width <= MOBILE_LAYOUT_BREAKPOINT;
  const sidebarHeight = `${MOBILE_SIDEBAR_HEIGHT_RATIO * 100}%`;
  const sidebarRef = React.useRef(null);
  const peekChromeRef = React.useRef(null);
  const collapsedYDebugRef = React.useRef(0);
  const collapsedYRef = React.useRef(0);
  const [collapsedY, setCollapsedY] = React.useState(0);

  React.useLayoutEffect(() => {
    if (!isMobile) {
      setCollapsedY(0);
      return;
    }
    const el = sidebarRef.current;
    const peek = peekChromeRef.current;
    if (!el) return;

    const measure = () => {
      const sidebarH = el.getBoundingClientRect().height;
      const peekH = peek
        ? peek.getBoundingClientRect().height
        : MOBILE_SIDEBAR_PEEK_PX;
      const nextY = Math.max(0, sidebarH - peekH);
      // #region agent log
      agentDebugBurst(
        'sidebar-measure',
        'Sidebar.jsx:measure',
        'ResizeObserver measure burst',
        { sidebarH, peekH, nextY },
        'A',
      );
      // #endregion
      const prevY = collapsedYDebugRef.current;
      if (prevY !== nextY) {
        // #region agent log
        agentDebugLog(
          'Sidebar.jsx:setCollapsedY',
          'collapsedY changed',
          { prev: prevY, nextY },
          'A',
        );
        // #endregion
        collapsedYDebugRef.current = nextY;
      }
      collapsedYRef.current = nextY;
      setCollapsedY((prev) => (prev === nextY ? prev : nextY));
      document.documentElement.style.setProperty('--mobile-sheet-peek', `${Math.ceil(peekH)}px`);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    if (peek) ro.observe(peek);
    window.addEventListener('resize', measure);
    window.addEventListener('orientationchange', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
      window.removeEventListener('orientationchange', measure);
    };
  }, [isMobile, sidebarHeight, viewport.height, viewport.width]);

  // Snap collapsed offset when peek height is remeasured (not on expand/collapse gesture).
  React.useLayoutEffect(() => {
    if (!isMobile) {
      sheetY.set(0);
      return;
    }
    if (isSidebarExpanded || collapsedY <= 0) return;
    sheetY.set(collapsedY);
  }, [collapsedY, isMobile, isSidebarExpanded, sheetY]);

  React.useEffect(() => {
    if (!isMobile) return;
    const y = collapsedYRef.current;
    const target = isSidebarExpanded ? 0 : y;
    if (!isSidebarExpanded && y <= 0) return;
    animate(sheetY, target, { type: 'spring', damping: 40, stiffness: 600 });
  }, [isSidebarExpanded, isMobile, sheetY]);

  const startSheetDrag = (e) => {
    if (!isMobile) return;
    dragControls.start(e);
  };

  return (
    <motion.aside
      ref={sidebarRef}
      className="sidebar"
      drag={isMobile ? 'y' : false}
      dragControls={dragControls}
      dragListener={false}
      dragConstraints={isMobile ? { top: 0, bottom: collapsedY } : undefined}
      dragElastic={isMobile ? 0.12 : 0}
      dragMomentum={false}
      onDragEnd={(_, info) => {
        if (!isMobile || collapsedY <= 0) return;
        const draggedDown = info.offset.y > 40 || info.velocity.y > 200;
        const draggedUp = info.offset.y < -40 || info.velocity.y < -200;
        if (draggedDown) setIsSidebarExpanded(false);
        else if (draggedUp) setIsSidebarExpanded(true);
        else setIsSidebarExpanded(sheetY.get() < collapsedY * 0.5);
      }}
      style={{
        y: sheetY,
        height: isMobile ? sidebarHeight : '100%',
      }}
    >
      <div
        ref={peekChromeRef}
        className="sidebar-drag-zone"
        role="button"
        tabIndex={0}
        aria-label="Drag to expand or collapse panel"
        onPointerDown={startSheetDrag}
      >
        <div className="sidebar-drag-handle" aria-hidden="true" />
      </div>
      <div className="sidebar-tabs">
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
        <AnimatePresence mode={isMobile ? 'sync' : 'wait'}>
          {activeTab === 'live' ? (
            <motion.div key="live-tab" initial={isMobile ? false : { opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={isMobile ? undefined : { opacity: 0, x: -20 }} className="live-panel">
              <div className="stats-card">
                <div className="card-header"><Navigation2 size={20} /><h2>ACTIVE THREATS</h2></div>
                <div className="stats-grid">
                  <div className="stat-item"><span className="label">EVENTS</span><span className="value">{liveEvents.length}</span></div>
                  <div className="stat-item"><span className="label">CLUSTERS</span><span className="value">{totalClusters}</span></div>
                  <div className="stat-item"><span className="label">TARGETS</span><span className="value">{totalTargets}</span></div>
                </div>
              </div>
              {liveEvents.length === 0 ? (
                <div className="empty-state"><RotateCcw size={48} color="#333" /><p>MONITORING AIRSPACE</p></div>
              ) : (
                <div className="alerts-list">
                  {liveEvents.map((ev, evIdx) => {
                    const alertKey = ev.id ?? `idx-${evIdx}`;
                    const isNewAlert = ev.id ? !seenLiveAlertIds.current.has(ev.id) : false;
                    if (ev.id) seenLiveAlertIds.current.add(ev.id);
                    const categoryColor = CATEGORY_COLORS[ev.category] || ev.visual_config?.color || '#ff944d';
                    const alertColor = (ev.category && `var(--${ev.category})`) || ev.visual_config?.color || '#ff944d';
                    const isGhost = ev.category === 'newsFlash';
                    const grouped = (ev.all_cities || []).reduce((acc, city) => {
                      const area = city.area || 'Other';
                      if (!acc[area]) acc[area] = [];
                      acc[area].push(city.name);
                      return acc;
                    }, {});

                    return (
                      <motion.div
                        key={alertKey}
                        initial={isNewAlert ? { x: 20, opacity: 0 } : false}
                        animate={{ x: 0, opacity: 1 }}
                        className={`alert-item live-active live-event-card${isGhost ? ' ghost-card' : ''}`}
                        style={{
                          borderLeftColor: categoryColor,
                          background: categoryTint(categoryColor),
                        }}
                      >
                        <div className="alert-marker" style={{ background: alertColor, boxShadow: `0 0 10px ${alertColor}` }}></div>
                        <div className="alert-info">
                          <h3 style={{ color: alertColor }}>{ev.title?.toUpperCase()} | {formatTime(ev.time)}</h3>
                          <div className="regional-breakdown-mini">
                            {Object.entries(grouped).map(([area, cities]) => (
                              <div key={area} className="area-group-mini">
                                <span className="area-label">{area}:</span>
                                <span className="area-cities">{cities.join(', ')}</span>
                              </div>
                            ))}
                          </div>
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
              <div className="history-filters">
                {[
                  { id: 'all', label: 'ALL', Icon: History },
                  { id: 'missiles', label: 'MISSILES', Icon: Rocket },
                  { id: 'hostileAircraftIntrusion', label: 'DRONES', Icon: Plane },
                  { id: 'terroristInfiltration', label: 'INFILTRATION', Icon: Users },
                  { id: 'earthQuake', label: 'QUAKE', Icon: Waves },
                ].map(({ id, label, Icon }) => (
                  <button
                    key={id}
                    className={`filter-tab ${historyFilter === id ? 'active' : ''}`}
                    data-category={id}
                    onClick={() => setHistoryFilter(id)}
                  >
                    <Icon size={14} />
                    <span>{label}</span>
                  </button>
                ))}              </div>

              <div className="timeframe-filters">
                {[
                  { id: 'all', label: 'All Time' },
                  { id: '1', label: 'Last 1H' },
                  { id: '12', label: 'Last 12H' },
                  { id: '24', label: 'Last 24H' },
                ].map(tf => (
                  <button
                    key={tf.id}
                    className={`filter-tab${tf.id === 'all' ? ' filter-all-time' : ''} ${timeFrame === tf.id ? 'active' : ''}`}
                    onClick={() => {
                      setTimeFrame(tf.id);
                      if (tf.id !== 'all') {
                        setViewMode('timeframe');
                        setMapConfig(calculateTimeframeMapConfig());
                      } else {
                        setViewMode('live');
                      }
                    }}
                  >
                    {tf.label}
                  </button>
                ))}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontSize: '10px', color: 'var(--text-sub)', fontWeight: '600' }}>FROM:</span>
                  <input
                    type="date"
                    style={{
                      background: 'rgba(255,255,255,0.08)',
                      border: '1px solid var(--border)',
                      color: 'white',
                      fontSize: '11px',
                      padding: '4px 6px',
                      width: 'auto',
                      minWidth: '105px',
                      borderRadius: '4px',
                      fontFamily: 'monospace'
                    }}
                    value={timeFrame.startsWith('range:') ? timeFrame.split(':')[1].split(',')[0] : ''}
                    onChange={(e) => {
                      const isoDate = e.target.value;
                      const currentTo = timeFrame.startsWith('range:') ? timeFrame.split(':')[1].split(',')[1] : '';
                      const newVal = `range:${isoDate},${currentTo}`;
                      setTimeFrame(newVal);
                      setViewMode('timeframe');
                      setMapConfig(calculateTimeframeMapConfig());
                    }}
                  />
                  <span style={{ fontSize: '10px', color: 'var(--text-sub)', fontWeight: '600' }}>TO:</span>
                  <input
                    type="date"
                    style={{
                      background: 'rgba(255,255,255,0.08)',
                      border: '1px solid var(--border)',
                      color: 'white',
                      fontSize: '11px',
                      padding: '4px 6px',
                      width: 'auto',
                      minWidth: '105px',
                      borderRadius: '4px',
                      fontFamily: 'monospace'
                    }}
                    value={timeFrame.startsWith('range:') ? timeFrame.split(':')[1].split(',')[1] : ''}
                    onChange={(e) => {
                      const isoDate = e.target.value;
                      const currentFrom = timeFrame.startsWith('range:') ? timeFrame.split(':')[1].split(',')[0] : '';
                      const newVal = `range:${currentFrom},${isoDate}`;
                      setTimeFrame(newVal);
                      setViewMode('timeframe');
                      setMapConfig(calculateTimeframeMapConfig());
                    }}
                  />
                </div>

                {timeFrame !== 'all' && (
                  <label className="merge-toggle" style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '9px', color: 'var(--text-sub)', marginLeft: 'auto', cursor: 'pointer', width: '100%' }}>
                    <input
                      type="checkbox"
                      checked={mergeTimeFrameClusters}
                      onChange={(e) => setMergeTimeFrameClusters(e.target.checked)}
                    />
                    MERGE CLUSTERS
                  </label>
                )}
              </div>

              {history.length === 0 ? (
                <div className="empty-state"><Clock size={48} color="#333" /><p>NO HISTORY RECORDED</p></div>
              ) : (
                <div className="history-list">
                  {sidebarEvents.map((event, i) => {
                    const isExpanded = expandedId === event.id;
                    const catIcon = {
                      'missiles': <Rocket size={16} />,
                      'newsFlash': <Rocket size={16} />,
                      'hostileAircraftIntrusion': <Plane size={16} />,
                      'hostileAircraft': <Plane size={16} />,
                      'aircraft': <Plane size={16} />,
                      'terroristInfiltration': <Users size={16} />,
                      'earthQuake': <Waves size={16} />
                    }[event.category || 'missiles'] || <ShieldAlert size={16} />;

                    const groupCitiesByArea = (cities) => {
                      if (!cities || !Array.isArray(cities) || !regionalData) return {};
                      const groups = {};
                      cities.forEach(c => {
                        const cityName = typeof c === 'string' ? c : c?.name;
                        if (!cityName) return;

                        let foundArea = "Other";
                        for (const [area, areaCities] of Object.entries(regionalData)) {
                          if (areaCities && typeof areaCities === 'object' && areaCities[cityName]) {
                            foundArea = area;
                            break;
                          }
                        }
                        if (!groups[foundArea]) groups[foundArea] = [];
                        groups[foundArea].push(cityName);
                      });
                      return groups;
                    };


                    const grouped = groupCitiesByArea(event.all_cities);

                    return (
                      <motion.div
                        key={event.id || `hist-${i}`}
                        className={`history-card ${archiveEvent?.id === event.id && viewMode === 'archive' ? 'selected' : ''} ${isExpanded ? 'active' : ''}`}
                        onClick={() => selectArchive(event)}
                      >
                        <div className="card-main">
                          <div
                            className="history-card-header"
                            role="button"
                            tabIndex={0}
                            aria-expanded={isExpanded}
                            onClick={(e) => {
                              e.stopPropagation();
                              selectArchive(event);
                              setExpandedId(isExpanded ? null : event.id);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                e.stopPropagation();
                                selectArchive(event);
                                setExpandedId(isExpanded ? null : event.id);
                              }
                            }}
                          >
                          <div className="history-marker" style={{ background: event.visual_config?.color || 'var(--accent)' }} />
                          <div className="card-content">
                            <div className="history-meta">
                              <span className="time">{event.timeRange || formatDateTime(event.time)}</span>
                              <span className="category-tag">{catIcon} {event.category?.toUpperCase()}</span>
                              {event.mergedCount > 1 && <span className="count-mini" style={{ background: 'var(--accent)', color: 'black', padding: '0 4px', borderRadius: '2px' }}>{event.mergedCount} EVENTS</span>}
                            </div>
                            <div className="history-title">{event.mergedCount > 1 ? `CONSOLIDATED ${event.category?.toUpperCase()} SALVO` : (event.title || 'Unknown Salvo')}</div>
                            {!isExpanded && (
                              <div className="time">
                                {Object.entries(grouped).map(([area, cities]) => (
                                  <div key={area} className="area-header">
                                    <span>{area}</span>
                                    <span className="count-mini">{cities.length}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                            <span className="history-card-chevron" aria-hidden="true">▾</span>
                          </div>
                        </div>

                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="card-details"
                            >
                              <div className="regional-breakdown">
                                {Object.entries(grouped).map(([area, cities]) => (
                                  <div key={area} className="area-group">
                                    <div className="area-header">
                                      <span>{area}</span>
                                      <span className="count-mini">{cities.length}</span>
                                    </div>
                                    <div className="area-cities-mini">
                                      {cities.map(c => <span key={c} className="city-pill-mini">{c}</span>)}
                                    </div>
                                  </div>
                                ))}
                              </div>
                              <div className="mission-id">MISSION_ID: {event.id}</div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    );
                  })}
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
  );
}
