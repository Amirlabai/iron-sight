import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Polygon, useMap } from 'react-leaflet';
import { Shield, Clock, MapPin, ChevronRight, CheckCircle, SplitSquareVertical, Filter, RefreshCcw, Combine } from 'lucide-react';
import { fetchHistory, updateAlertOrigin, splitAlert, mergeAlerts, suggestOrigin, fetchTrainingExport } from './api/apiService';
import {
  ISRAEL_CENTER, DEFAULT_ZOOM, TACTICAL_RED, HIGHLIGHT_RED, ORIGINS_DATA,
  STRATEGIC_METADATA, TACTICAL_API_URL, API_PROXY_TARGET,
} from './utils/constants';
import { fetchHealth } from './api/apiService';
import { TACTICAL_BOUNDARIES } from './utils/tactical_geodata';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Fix Leaflet icons
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

function MapCenterer({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.setView(center, zoom || DEFAULT_ZOOM);
  }, [center, zoom, map]);
  return null;
}

function cityCount(ev) {
  return (ev.all_cities || []).length;
}

function passesCityCountFilter(ev, minCities, maxCities) {
  const n = cityCount(ev);
  const min = minCities === '' ? null : Number(minCities);
  const max = maxCities === '' ? null : Number(maxCities);
  if (min !== null && Number.isFinite(min) && n < min) return false;
  if (max !== null && Number.isFinite(max) && n > max) return false;
  return true;
}

function App() {
  const [history, setHistory] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [hideVerified, setHideVerified] = useState(false);
  const [queueFilter, setQueueFilter] = useState('all');
  const [minCities, setMinCities] = useState('');
  const [maxCities, setMaxCities] = useState('');
  const [originMarker, setOriginMarker] = useState(null);
  const [originName, setOriginName] = useState('Gaza');
  const [mlSuggestion, setMlSuggestion] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [apiOnline, setApiOnline] = useState(null);

  useEffect(() => {
    loadHistory();
  }, [filter]);

  const loadHistory = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      try {
        await fetchHealth();
        setApiOnline(true);
      } catch (healthErr) {
        setApiOnline(false);
        throw new Error(
          `Cannot reach API via ${TACTICAL_API_URL}/api (proxy → ${API_PROXY_TARGET}). ` +
          `Ensure backend is running on port 8080, then restart Vite. ${healthErr.message}`,
        );
      }

      const rows = await fetchHistory(filter);
      setHistory(rows);
      if (rows.length > 0) {
        await selectEvent(rows[0]);
      } else {
        setSelectedEvent(null);
        setOriginMarker(null);
        setMlSuggestion(null);
      }
    } catch (err) {
      console.error('HISTORY_LOAD_FAILED:', err);
      setLoadError(err.message || String(err));
      setHistory([]);
      setSelectedEvent(null);
    } finally {
      setLoading(false);
    }
  };

  const selectEvent = async (event) => {
    setSelectedEvent(event);
    const traj = event.trajectories?.[0];
    if (traj) {
      setOriginMarker(traj.marker_coords || traj.origin_coords);
      setOriginName(traj.origin);
    }
    setMlSuggestion(null);
    if (event.category === 'missiles' && event.all_cities?.length) {
      try {
        const suggestion = await suggestOrigin({
          id: event.id,
          category: event.category,
          allow_strategic: true,
        });
        if (suggestion.suggested) {
          setMlSuggestion(suggestion);
          if (!event.verified && suggestion.suggested) {
            setOriginName(suggestion.suggested);
            const pin = ORIGINS_DATA[suggestion.suggested] || ORIGINS_DATA['Lebanon'];
            setOriginMarker(pin);
          }
        }
      } catch (err) {
        console.warn('ML_SUGGEST_FAILED', err);
      }
    }
  };

  const toggleSelection = (id, e) => {
    e.stopPropagation();
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const handleMarkerDrag = (e) => {
    const latlng = e.target.getLatLng();
    setOriginMarker([latlng.lat, latlng.lng]);
  };

  const displayedHistory = useMemo(() => history.filter((ev) => {
    if (hideVerified && ev.verified) return false;
    if (queueFilter === 'needs_review' && ev.verified) return false;
    if (queueFilter === 'newsFlash' && ev.category !== 'newsFlash') return false;
    if (queueFilter === 'multi_origin') {
      const cands = ev.origin_candidates || [];
      const trajCount = (ev.trajectories || []).length;
      if (!(cands.length >= 2 || trajCount >= 2)) return false;
    }
    if (queueFilter === 'low_confidence') {
      const conf = ev.origin_ml_confidence;
      if (!(conf !== undefined && conf !== null && conf < 0.5)) return false;
    }
    return passesCityCountFilter(ev, minCities, maxCities);
  }), [history, hideVerified, queueFilter, minCities, maxCities]);

  const cityFilterActive = minCities !== '' || maxCities !== '';

  useEffect(() => {
    if (loading || loadError) return;
    if (displayedHistory.length === 0) {
      setSelectedEvent(null);
      setOriginMarker(null);
      setMlSuggestion(null);
      return;
    }
    if (!selectedEvent || !displayedHistory.some((e) => e.id === selectedEvent.id)) {
      selectEvent(displayedHistory[0]);
    }
  }, [displayedHistory, loading, loadError, selectedEvent?.id]);

  const handleVerify = async () => {
    if (!selectedEvent || !originMarker) return;
    setLoading(true);
    try {
      const resp = await updateAlertOrigin(
        selectedEvent.id,
        selectedEvent.category,
        originName,
        originMarker,
        mlSuggestion?.scores || selectedEvent.origin_ml_scores || null
      );
      if (resp.status === 'SUCCESS') {
        const updatedEvent = resp.event;
        // FULL state sync
        setHistory(prev => prev.map(h => 
          h.id === updatedEvent.id ? updatedEvent : h
        ));
        setSelectedEvent(updatedEvent);
        
        // Auto-select next unverified if available
        if (hideVerified) {
          const nextIndex = history.findIndex(h => h.id === selectedEvent.id) + 1;
          const next = history.slice(nextIndex).find(h => !h.verified);
          if (next) selectEvent(next);
        }
      }
    } catch (err) {
      alert("Update failed: " + err);
    } finally {
      setLoading(false);
    }
  };

  const handleSplit = async () => {
    if (!selectedEvent) return;
    if (!confirm("Are you sure you want to remove this merged group? It will need to be re-processed or split manually in the DB.")) return;
    
    setLoading(true);
    try {
      const resp = await splitAlert(selectedEvent.id, selectedEvent.category);
      if (resp.status === 'SUCCESS') {
        alert("Event removed successfully.");
        setSelectedEvent(null);
        loadHistory();
      }
    } catch (err) {
      alert("Split failed: " + err);
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async () => {
    if (selectedIds.size < 2) return;
    
    const selectedEvents = history.filter(h => selectedIds.has(h.id));
    const categories = new Set(selectedEvents.map(e => e.category));
    
    if (categories.size > 1) {
      alert("Operational Conflict: Cannot merge different threat categories (e.g. Missiles and Drones).");
      return;
    }
    
    const category = Array.from(categories)[0];
    if (!confirm(`Merge ${selectedIds.size} ${category} records into a single tactical event? (Originals will be purged)`)) return;
    
    setLoading(true);
    try {
      const resp = await mergeAlerts(Array.from(selectedIds), category);
      if (resp.status === 'SUCCESS') {
        setSelectedIds(new Set());
        loadHistory();
      }
    } catch (err) {
      alert("Merge failed: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="history-auditor">
      <header className="auditor-header">
        <div className="flex items-center gap-2">
          <Shield className="text-blue-500" />
          <h1>IRON SIGHT <span>HISTORY AUDITOR</span></h1>
        </div>
        <div className="header-controls">
          <button 
            className={`filter-toggle ${hideVerified ? 'active' : ''}`}
            onClick={() => setHideVerified(!hideVerified)}
          >
            {hideVerified ? <CheckCircle size={14} /> : <Filter size={14} />}
            {hideVerified ? 'HIDE VERIFIED: ON' : 'SHOW ALL'}
          </button>
          
          <button onClick={() => loadHistory()} className="icon-btn" title="Reload History">
            <RefreshCcw size={16} />
          </button>
          
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All Threats</option>
            <option value="missiles">Missiles</option>
            <option value="newsFlash">News Flash</option>
            <option value="hostileAircraftIntrusion">Drones</option>
            <option value="terroristInfiltration">Infiltration</option>
            <option value="earthQuake">Earthquake</option>
          </select>

          <select value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)} title="Training queue">
            <option value="all">Queue: All</option>
            <option value="needs_review">Needs review</option>
            <option value="multi_origin">Multi-origin</option>
            <option value="low_confidence">Low ML confidence</option>
            <option value="newsFlash">News flash only</option>
          </select>

          <button
            className="icon-btn"
            title="Export verified training JSON"
            onClick={async () => {
              try {
                const data = await fetchTrainingExport('missiles', 'json');
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'training_export.json';
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) {
                alert('Export failed: ' + e);
              }
            }}
          >
            Export
          </button>

          {selectedIds.size >= 2 && (
            <button className="merge-btn active" onClick={handleMerge}>
              <Combine size={14} /> MERGE ({selectedIds.size})
            </button>
          )}
        </div>
      </header>

      <main className="auditor-main">
        <aside className="event-sidebar">
          <div className="sidebar-header">
            <Filter size={14} />
            <span>
              EVENTS {displayedHistory.length}
              {history.length !== displayedHistory.length && ` / ${history.length}`}
            </span>
          </div>
          <div className="sidebar-filters">
            <label className="sidebar-filter-label" htmlFor="min-cities">Cities</label>
            <input
              id="min-cities"
              type="number"
              min={0}
              className="city-filter-input"
              placeholder="Min"
              value={minCities}
              onChange={(e) => setMinCities(e.target.value)}
              title="Minimum number of cities"
            />
            <span className="city-filter-sep">–</span>
            <input
              id="max-cities"
              type="number"
              min={0}
              className="city-filter-input"
              placeholder="Max"
              value={maxCities}
              onChange={(e) => setMaxCities(e.target.value)}
              title="Maximum number of cities"
            />
            {cityFilterActive && (
              <button
                type="button"
                className="city-filter-clear"
                onClick={() => { setMinCities(''); setMaxCities(''); }}
                title="Clear city filter"
              >
                Clear
              </button>
            )}
          </div>
          <div className="event-list">
            {loading && (
              <div className="sidebar-status">Loading archive…</div>
            )}
            {!loading && loadError && (
              <div className="sidebar-status sidebar-status-error">
                <p>{loadError}</p>
                <p className="sidebar-hint">
                  UI: {TACTICAL_API_URL}/api → backend {API_PROXY_TARGET}
                </p>
              </div>
            )}
            {!loading && !loadError && history.length === 0 && (
              <div className="sidebar-status">
                Archive returned no events. Check MongoDB and category filter.
              </div>
            )}
            {!loading && !loadError && history.length > 0 && displayedHistory.length === 0 && (
              <div className="sidebar-status">
                {history.length} loaded; none match the current filters
                {cityFilterActive && ` (cities ${minCities || '0'}–${maxCities || '∞'})`}.
              </div>
            )}
            {displayedHistory.map(ev => (
              <div 
                key={ev.id} 
                className={`event-card ${selectedEvent?.id === ev.id ? 'active' : ''} ${ev.verified ? 'verified' : ''} ${selectedIds.has(ev.id) ? 'selected' : ''}`}
                onClick={() => selectEvent(ev)}
              >
                <div className="selection-area" onClick={(e) => toggleSelection(ev.id, e)}>
                  <input 
                    type="checkbox" 
                    checked={selectedIds.has(ev.id)} 
                    onChange={() => {}} // Handled by onClick on parent
                  />
                </div>
                <div className="card-content">
                  <div className="event-meta">
                    <span className="event-time">{ev.time || '00:00:00'}</span>
                    <span className="event-id">#{ev.id}</span>
                  </div>
                  <div className="event-title">
                    {ev.title || ev.category}
                    {ev.verified && <CheckCircle size={14} className="text-green-500 ml-auto" />}
                  </div>
                  <div className="event-details">
                    {ev.all_cities?.length} Cities • {ev.manual_origin || ev.trajectories?.[0]?.origin || 'Unknown'}
                    {ev.lifecycle_status ? ` • ${ev.lifecycle_status}` : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <section className="map-view">
          <MapContainer center={ISRAEL_CENTER} zoom={DEFAULT_ZOOM} style={{ height: '100%', width: '100%' }}>
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
            <MapCenterer center={selectedEvent?.center} />
            
            {selectedEvent && (
              <>
                {/* Origin Highlights */}
                {selectedEvent.trajectories?.map((traj, idx) => {
                  const boundary = TACTICAL_BOUNDARIES[traj.origin];
                  if (!boundary) return null;
                  const color = STRATEGIC_METADATA[traj.origin]?.color || HIGHLIGHT_RED;
                  return (
                    <React.Fragment key={`highlight-${idx}`}>
                      <Polygon 
                        positions={boundary} 
                        pathOptions={{ color, weight: 15, opacity: 0.05, fill: false, className: 'origin-threat-halo' }} 
                      />
                      <Polygon 
                        positions={boundary} 
                        pathOptions={{ fillColor: color, fillOpacity: 0.1, color, weight: 1, className: 'origin-threat-glow' }} 
                      />
                    </React.Fragment>
                  );
                })}

                {/* Cluster Points (Safety Guarded) */}
                {selectedEvent.all_cities?.filter(c => c.coords).map((city, idx) => (
                  <Marker key={idx} position={city.coords} icon={L.divIcon({ className: 'city-pulse-dot' })}>
                    <Popup>{city.name}</Popup>
                  </Marker>
                ))}

                {/* Tracking Line */}
                {originMarker && selectedEvent?.center && (
                  <Polyline 
                    positions={[originMarker, selectedEvent.center]} 
                    color={HIGHLIGHT_RED} 
                    weight={2} 
                    dashArray="5, 10" 
                  />
                )}

                {/* Draggable Origin Marker */}
                {originMarker && (
                  <Marker 
                    position={originMarker} 
                    draggable={true} 
                    eventHandlers={{ dragend: handleMarkerDrag }}
                  >
                    <Popup>
                      <div className="origin-popup">
                        <strong>ORIGIN: {originName}</strong>
                        <p>Drag to fix position</p>
                      </div>
                    </Popup>
                  </Marker>
                )}
              </>
            )}
          </MapContainer>
        </section>

        <aside className="control-panel">
          {selectedEvent ? (
            <div className="control-content">
              <h3>TACTICAL AUDIT</h3>
              <div className="data-group">
                <label>EVENT ID</label>
                <div>{selectedEvent.id}</div>
              </div>
              <div className="data-group">
                <label>CATEGORY</label>
                <div className="capitalize">{selectedEvent.category}</div>
              </div>
              
              {mlSuggestion && Object.keys(mlSuggestion.scores || {}).length > 0 && (
                <div className="data-group ml-scores-panel">
                  <label>ML ORIGIN SCORES</label>
                  <div className="ml-scores-list">
                    {Object.entries(mlSuggestion.scores).map(([origin, score]) => (
                      <button
                        key={origin}
                        type="button"
                        className={`ml-score-row ${origin === mlSuggestion.suggested ? 'suggested' : ''}`}
                        onClick={() => {
                          setOriginName(origin);
                          setOriginMarker(ORIGINS_DATA[origin] || ORIGINS_DATA['Lebanon']);
                        }}
                      >
                        <span>{origin}</span>
                        <span>{typeof score === 'number' ? score.toFixed(3) : score}</span>
                      </button>
                    ))}
                  </div>
                  <div className="mono-text">
                    Suggested: {mlSuggestion.suggested} ({mlSuggestion.resolved_by})
                    {mlSuggestion.confidence != null && ` conf=${Number(mlSuggestion.confidence).toFixed(2)}`}
                  </div>
                </div>
              )}

              <div className="data-group">
                <label>ORIGIN LABEL</label>
                <select 
                  value={originName} 
                  onChange={(e) => {
                    const newOrigin = e.target.value;
                    setOriginName(newOrigin);
                    const defaultCoords = ORIGINS_DATA[newOrigin] || ORIGINS_DATA["Iran"];
                    setOriginMarker(defaultCoords);
                  }}
                >
                  {Object.keys(ORIGINS_DATA).map(o => <option key={o} value={o}>{o}</option>)}
                  <option value="North Iran">North Iran</option>
                  <option value="Iraq">Iraq</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="data-group">
                <label>COORDINATES</label>
                <div className="mono-text">
                  {originMarker ? `${originMarker[0].toFixed(4)}, ${originMarker[1].toFixed(4)}` : 'N/A'}
                </div>
              </div>

              <div className="action-buttons">
                <button 
                  className="verify-btn" 
                  onClick={handleVerify} 
                  disabled={loading}
                >
                  <CheckCircle size={18} /> COMMIT & VERIFY
                </button>
                
                <button 
                  className="split-btn" 
                  onClick={handleSplit}
                  disabled={loading}
                >
                  <SplitSquareVertical size={18} /> SPLIT / REMOVE
                </button>
              </div>

              <div className="cities-breakdown">
                <label>
                  CITIES ({selectedEvent.all_cities?.length})
                  <button
                    type="button"
                    className="copy-cities-btn"
                    onClick={() => {
                      const text = (selectedEvent.all_cities || []).map((c) => c.name).join(', ');
                      navigator.clipboard?.writeText(text);
                    }}
                  >
                    Copy
                  </button>
                </label>
                <div className="city-chips">
                  {selectedEvent.all_cities?.map((c, i) => (
                    <span key={i} className="city-chip">{c.name}</span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <Clock size={48} />
              <p>Select an event to begin audit</p>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

export default App;
