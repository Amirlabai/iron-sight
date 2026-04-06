import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import { Shield, Clock, MapPin, ChevronRight, CheckCircle, SplitSquareVertical, Filter, RefreshCcw } from 'lucide-react';
import { fetchHistory, updateAlertOrigin, splitAlert, fetchCities } from './api/apiService';
import { ISRAEL_CENTER, DEFAULT_ZOOM, TACTICAL_RED, HIGHLIGHT_RED, ORIGINS_DATA } from './utils/constants';
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

function App() {
  const [history, setHistory] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [hideVerified, setHideVerified] = useState(false);
  const [originMarker, setOriginMarker] = useState(null);
  const [originName, setOriginName] = useState('Gaza');

  useEffect(() => {
    loadHistory();
  }, [filter]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchHistory(filter);
      setHistory(data);
      if (data.length > 0 && !selectedEvent) {
        selectEvent(data[0]);
      }
    } catch (err) {
      console.error("HISTORY_LOAD_FAILED:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectEvent = (event) => {
    setSelectedEvent(event);
    const traj = event.trajectories?.[0];
    if (traj) {
      setOriginMarker(traj.marker_coords || traj.origin_coords);
      setOriginName(traj.origin);
    }
  };

  const handleMarkerDrag = (e) => {
    const latlng = e.target.getLatLng();
    setOriginMarker([latlng.lat, latlng.lng]);
  };

  const displayedHistory = hideVerified 
    ? history.filter(ev => !ev.verified) 
    : history;

  const handleVerify = async () => {
    if (!selectedEvent || !originMarker) return;
    setLoading(true);
    try {
      const resp = await updateAlertOrigin(
        selectedEvent.id, 
        selectedEvent.category, 
        originName, 
        originMarker
      );
      if (resp.status === 'SUCCESS') {
        // Optimistic update
        setHistory(prev => prev.map(h => 
          h.id === selectedEvent.id ? { ...h, verified: true } : h
        ));
        
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
            <option value="hostileAircraftIntrusion">Drones</option>
          </select>
        </div>
      </header>

      <main className="auditor-main">
        <aside className="event-sidebar">
          <div className="sidebar-header">
            <Filter size={14} /> 
            <span>TACTICAL EVENTS ({displayedHistory.length})</span>
          </div>
          <div className="event-list">
            {displayedHistory.map(ev => (
              <div 
                key={ev.id} 
                className={`event-card ${selectedEvent?.id === ev.id ? 'active' : ''} ${ev.verified ? 'verified' : ''}`}
                onClick={() => selectEvent(ev)}
              >
                <div className="event-meta">
                  <span className="event-time">{ev.time || '00:00:00'}</span>
                  <span className="event-id">#{ev.id}</span>
                </div>
                <div className="event-title">
                  {ev.category === 'missiles' ? 'Rocket Salvo' : 'Drone Intrusion'}
                  {ev.verified && <CheckCircle size={14} className="text-green-500 ml-auto" />}
                </div>
                <div className="event-details">
                  {ev.all_cities?.length} Cities • {ev.trajectories?.[0]?.origin || 'Unknown'}
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
                {/* Cluster Points */}
                {selectedEvent.all_cities?.map((city, idx) => (
                  <Marker key={idx} position={city.coords} icon={L.divIcon({ className: 'city-pulse-dot' })}>
                    <Popup>{city.name}</Popup>
                  </Marker>
                ))}

                {/* Tracking Line */}
                {originMarker && selectedEvent.center && (
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
              
              <div className="data-group">
                <label>ORIGIN LABEL</label>
                <select value={originName} onChange={(e) => setOriginName(e.target.value)}>
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
                <label>CITIES ({selectedEvent.all_cities?.length})</label>
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
