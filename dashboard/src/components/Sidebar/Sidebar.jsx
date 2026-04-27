import React from 'react';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import {
  Activity, ShieldAlert, Navigation2, RotateCcw, History,
  Clock, Shield, ChevronDown, ChevronRight, Terminal,
  Rocket, Plane, Zap, Wind, Users, Waves
} from 'lucide-react';
import { useTactical } from '../../context/TacticalContext';

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
    historyFilter, setHistoryFilter, fetchHistory
  } = useTactical();

  const [expandedId, setExpandedId] = React.useState(null);

  React.useEffect(() => {
    setExpandedId(null);
  }, [historyFilter]);

  const dragControls = useDragControls();

  return (
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
                    const alertColor = ev.visual_config?.color || '#ff944d';
                    const grouped = (ev.all_cities || []).reduce((acc, city) => {
                      const area = city.area || 'Other';
                      if (!acc[area]) acc[area] = [];
                      acc[area].push(city.name);
                      return acc;
                    }, {});

                    return (
                      <motion.div
                        key={ev.id || evIdx}
                        initial={{ x: 20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        className="alert-item live-active"
                        style={{ borderLeftColor: alertColor }}
                      >
                        <div className="alert-marker" style={{ background: alertColor, boxShadow: `0 0 10px ${alertColor}` }}></div>
                        <div className="alert-info">
                          <h3 style={{ color: alertColor }}>{ev.title?.toUpperCase()} | {ev.time}</h3>
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
                    onClick={() => setHistoryFilter(id)}
                  >
                    <Icon size={14} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>

              {history.length === 0 ? (
                <div className="empty-state"><Clock size={48} color="#333" /><p>NO HISTORY RECORDED</p></div>
              ) : (
                <div className="history-list">
                  {history.map((event, i) => {
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
                        onClick={() => {
                          selectArchive(event);
                          setExpandedId(isExpanded ? null : event.id);
                        }}
                      >
                        <div className="card-main">
                          <div className="history-marker" style={{ background: event.visual_config?.color || 'var(--accent)' }}></div>
                          <div className="card-content">
                            <div className="history-meta">
                              <span className="time">{event.time}</span>
                              <span className="category-tag">{catIcon} {event.category?.toUpperCase()}</span>
                            </div>
                            <div className="history-title">{event.title || 'Unknown Salvo'}</div>
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
                          {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
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
