// Mobile bottom sheet: collapsed = fully hidden; expand via sidebar-expand-btn.
import React from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, animate } from 'framer-motion';
import {
  Activity, ShieldAlert, Navigation2, RotateCcw, History,
  Clock,
  Rocket, Plane, Zap, Wind, Users, Waves
} from 'lucide-react';
import { useTactical } from '../../context/TacticalContext';
import { formatTime, formatDateTime, dateToDisplay, displayToDate } from '../../utils/formatters';
import {
  CATEGORY_COLORS,
  categoryTint,
  MOBILE_LAYOUT_BREAKPOINT,
  MOBILE_SIDEBAR_HEIGHT_RATIO,
} from '../../utils/constants';
import { calculateTimeframeMapConfig } from '../../utils/mapGeometry';
import { ORIGIN_FILTER_OPTIONS } from '../../utils/mapZoomPresets';
import { agentDebugBurst, agentDebugLog } from '../../utils/agentDebugLog';
import { useViewportSize } from '../../hooks/useViewportSize';
import DateRangeFilter from './DateRangeFilter';
import FilterCarousel, { isTimeframePreset } from './FilterCarousel';

const HISTORY_FILTER_ITEMS = [
  { id: 'all', label: 'ALL', Icon: History },
  { id: 'missiles', label: 'MISSILES', Icon: Rocket },
  { id: 'hostileAircraftIntrusion', label: 'DRONES', Icon: Plane },
  { id: 'terroristInfiltration', label: 'INFILTRATION', Icon: Users },
  { id: 'earthQuake', label: 'QUAKE', Icon: Waves },
];

const TIMEFRAME_FILTER_ITEMS = [
  { id: 'all', label: 'All Time' },
  { id: '1', label: 'Last 1H' },
  { id: '12', label: 'Last 12H' },
  { id: '24', label: 'Last 24H' },
];

const ORIGIN_FILTER_ITEMS = [
  { id: 'all', label: 'ALL ORIGINS' },
  ...ORIGIN_FILTER_OPTIONS.map((origin) => ({
    id: origin,
    label: origin.toUpperCase(),
  })),
];

export default function Sidebar() {
  const {
    activeTab, handleTabChange, liveEvents, history,
    viewMode, archiveEvent, selectArchive,
    regionalData,
    isSidebarExpanded,
    setIsSidebarExpanded,
    totalClusters, totalTargets,

    historyFilter, setHistoryFilter,
    timeFrame, setTimeFrame, originFilter, setOriginFilter, filteredHistory, originFilterLoading,
    mergeTimeFrameClusters, setMergeTimeFrameClusters, setViewMode, setMapConfig,
    renderableEvents, sidebarEvents,
    historyHasMore, historyLoadingMore, loadMoreHistory,
  } = useTactical();

  const [expandedId, setExpandedId] = React.useState(null);
  const seenLiveAlertIds = React.useRef(new Set());

  React.useEffect(() => {
    setExpandedId(null);
  }, [historyFilter]);

  const dragControls = useDragControls();
  const sheetY = useMotionValue(0);

  const viewport = useViewportSize();

  const isMobile = viewport.width <= MOBILE_LAYOUT_BREAKPOINT;
  const sidebarHeight = `${MOBILE_SIDEBAR_HEIGHT_RATIO * 100}%`;
  const sidebarRef = React.useRef(null);
  const collapsedYDebugRef = React.useRef(0);
  const collapsedYRef = React.useRef(0);
  const [collapsedY, setCollapsedY] = React.useState(0);

  React.useLayoutEffect(() => {
    if (!isMobile) {
      setCollapsedY(0);
      return;
    }
    const el = sidebarRef.current;
    if (!el) return;

    const measure = () => {
      const sidebarH = el.getBoundingClientRect().height;
      const nextY = sidebarH;
      // #region agent log
      agentDebugBurst(
        'sidebar-measure',
        'Sidebar.jsx:measure',
        'ResizeObserver measure burst',
        { sidebarH, nextY },
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
      document.documentElement.style.setProperty('--mobile-sheet-peek', '0px');
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
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
    const y = collapsedYRef.current || collapsedY;
    const target = isSidebarExpanded ? 0 : y;
    if (!isSidebarExpanded && y <= 0) return;
    animate(sheetY, target, { type: 'spring', damping: 40, stiffness: 600 });
  }, [isSidebarExpanded, isMobile, sheetY, collapsedY]);

  const startSheetDrag = (e) => {
    if (!isMobile) return;
    dragControls.start(e);
  };

  const historyShowMoreFooter = historyHasMore ? (
    <div className="history-show-more-footer">
      <button
        type="button"
        className="history-show-more-btn"
        onClick={loadMoreHistory}
        disabled={historyLoadingMore}
      >
        {historyLoadingMore ? 'LOADING...' : 'SHOW MORE'}
      </button>
    </div>
  ) : null;

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

      <div className="sidebar-tabs" onPointerDown={startSheetDrag}>
        <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabChange('live'); }}>
          <Activity size={18} /> LIVE
        </button>
        <button className={`tab-btn ${activeTab === 'archive' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabChange('archive'); }}>
          <History size={18} /> HISTORY
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
          ) : (
            <motion.div key="history-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="archive-panel">
              <FilterCarousel
                className="history-filters"
                ariaLabel="History category filter"
                enabled={isMobile}
                value={historyFilter}
                onChange={setHistoryFilter}
                items={HISTORY_FILTER_ITEMS}
                renderItem={({ id, label, Icon }, { isSelected, onSelect }) => (
                  <button
                    type="button"
                    className={`filter-tab ${isSelected ? 'active' : ''}`}
                    data-category={id}
                    role="option"
                    aria-selected={isSelected}
                    onClick={onSelect}
                  >
                    <Icon size={14} />
                    <span>{label}</span>
                  </button>
                )}
              />

              <div className={`timeframe-filters${isMobile ? ' timeframe-filters--mobile' : ''}`}>
                <FilterCarousel
                  className={isMobile ? 'timeframe-filters-carousel' : 'timeframe-filters-presets'}
                  ariaLabel="History timeframe filter"
                  enabled={isMobile}
                  value={isTimeframePreset(timeFrame) ? timeFrame : null}
                  items={TIMEFRAME_FILTER_ITEMS}
                  onChange={(tf) => {
                    setTimeFrame(tf);
                    if (tf !== 'all') {
                      setViewMode('timeframe');
                      setMapConfig(calculateTimeframeMapConfig());
                    } else {
                      setViewMode('live');
                    }
                  }}
                  renderItem={({ id, label }, { isSelected, onSelect }) => (
                    <button
                      type="button"
                      className={`filter-tab${id === 'all' ? ' filter-all-time' : ''} ${isSelected ? 'active' : ''}`}
                      role="option"
                      aria-selected={isSelected}
                      onClick={onSelect}
                    >
                      {label}
                    </button>
                  )}
                />
                <div className="timeframe-filters-extra">
                  <DateRangeFilter
                    timeFrame={timeFrame}
                    onTimeFrameChange={(newVal) => {
                      setTimeFrame(newVal);
                      setViewMode('timeframe');
                      setMapConfig(calculateTimeframeMapConfig());
                    }}
                  />
                  {timeFrame !== 'all' && (
                    <label className="merge-toggle">
                      <input
                        type="checkbox"
                        checked={mergeTimeFrameClusters}
                        onChange={(e) => setMergeTimeFrameClusters(e.target.checked)}
                      />
                      MERGE CLUSTERS
                    </label>
                  )}
                </div>
              </div>

              <FilterCarousel
                className="origin-filters"
                ariaLabel="Launch origin filter"
                enabled={isMobile}
                value={originFilter}
                onChange={setOriginFilter}
                items={ORIGIN_FILTER_ITEMS}
                renderItem={({ id, label }, { isSelected, onSelect }) => (
                  <button
                    type="button"
                    className={`filter-tab filter-tab-origin ${isSelected ? 'active' : ''}`}
                    role="option"
                    aria-selected={isSelected}
                    onClick={onSelect}
                  >
                    {label}
                  </button>
                )}
              />

              {history.length === 0 && !historyHasMore ? (
                <div className="empty-state"><Clock size={48} color="#333" /><p>NO HISTORY RECORDED</p></div>
              ) : filteredHistory.length === 0 && !historyHasMore && originFilter !== 'all' ? (
                <div className="empty-state"><Clock size={48} color="#333" /><p>NO EVENTS FOR THIS ORIGIN</p></div>
              ) : (
                <div className="archive-panel-body">
                  <div className="history-list">
                    {filteredHistory.length === 0 && originFilter !== 'all' ? (
                      <p className="history-origin-empty-hint">
                        {originFilterLoading
                          ? `Loading more archive pages for ${originFilter}…`
                          : `No ${originFilter} events in loaded pages yet.`}
                      </p>
                    ) : null}
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
                  {historyShowMoreFooter}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  );
}
