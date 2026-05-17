import React from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, useMap, useMapEvents, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { ISRAEL_CENTER, DEFAULT_ZOOM, TACTICAL_BOUNDARIES, STRATEGIC_METADATA } from '../../utils/constants';
import { useTactical } from '../../context/TacticalContext';
import { formatTime } from '../../utils/formatters';
import ThreatOverlay from './ThreatOverlay';

function MapController({ center, zoom }) {
  const map = useMap();
  const prevRef = React.useRef('');
  React.useEffect(() => {
    const key = `${center[0]},${center[1]},${zoom}`;
    if (key !== prevRef.current) {
      prevRef.current = key;
      map.flyTo(center, zoom, { duration: 1.5 });
    }
  }, [center, zoom, map]);
  return null;
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: () => onMapClick(),
  });
  return null;
}

export default function MapViewer() {
  const {
    mapConfig, renderableEvents, viewMode, archiveEvent,
    hasSimulation, tacticalColor, highlightColor,
    setIsSidebarExpanded
  } = useTactical();

  return (
    <div className="map-wrapper">
      <div className="map-overlay-info">
        {viewMode === 'archive' && <div className="archive-watermark">HISTORICAL DATA REWIND | {formatTime(archiveEvent?.time)}</div>}
        {viewMode === 'sandbox' && <div className="sandbox-watermark">DRY RUN ANALYSIS | Hypo-Salvo</div>}
        {hasSimulation && viewMode === 'live' && <div className="sandbox-watermark" style={{ color: '#ff9500', borderColor: '#ff9500' }}>SIMULATION EXERCISE ACTIVE</div>}
      </div>
      <MapContainer
        center={ISRAEL_CENTER}
        zoom={DEFAULT_ZOOM}
        className="leaflet-container"
        zoomControl={false}
        attributionControl={false}
        preferCanvas={true}
      >
        <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png" />

        <MapController center={mapConfig.center} zoom={mapConfig.zoom} />
        <ZoomControl position="bottomright" />
        <MapClickHandler onMapClick={() => { if (window.innerWidth <= 1024) setIsSidebarExpanded(false); }} />

        {/* Israel Base Layer */}
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

        {/* Origin Highlights for Timeframe Mode (Unified) */}
        {viewMode === 'timeframe' && (() => {
          const uniqueOrigins = new Set();
          renderableEvents.forEach(ev => {
            ev.trajectories?.forEach(t => uniqueOrigins.add(t.origin));
            ev.highlight_origins?.forEach(o => uniqueOrigins.add(o.name));
            // Also check cluster origin if trajectories are missing
            if (ev.clusters?.[0]?.origin) uniqueOrigins.add(ev.clusters[0].origin);
          });
          return Array.from(uniqueOrigins).map(origin => {
            const boundary = TACTICAL_BOUNDARIES[origin];
            const color = STRATEGIC_METADATA[origin]?.color || tacticalColor;
            if (!boundary) return null;
            return (
              <React.Fragment key={`timeframe-origin-${origin}`}>
                <Polygon positions={boundary} pathOptions={{ color, weight: 15, opacity: 0.05, fill: false, className: 'origin-threat-halo' }} />
                <Polygon positions={boundary} pathOptions={{ fillColor: color, fillOpacity: 0.1, color, weight: 1, className: 'origin-threat-glow' }} />
              </React.Fragment>
            );
          });
        })()}

        {/* Unified Origin Pins for Timeframe Mode */}
        {viewMode === 'timeframe' && (() => {
          const originData = {};
          renderableEvents.forEach(ev => {
            ev.trajectories?.forEach(t => {
              if (!originData[t.origin]) {
                originData[t.origin] = {
                  coords: t.marker_coords || t.origin_coords || [31.0, 35.0],
                  color: (ev.category && `var(--${ev.category})`) || ev.visual_config?.color || STRATEGIC_METADATA[t.origin]?.color || tacticalColor
                };
              }
            });
            ev.highlight_origins?.forEach(o => {
              if (!originData[o.name]) {
                originData[o.name] = {
                  coords: o.coords || [31.0, 35.0],
                  color: STRATEGIC_METADATA[o.name]?.color || tacticalColor
                };
              }
            });
            // Handle cluster-only origins for pins
            if (ev.clusters?.[0]?.origin && !originData[ev.clusters[0].origin]) {
              const origin = ev.clusters[0].origin;
              originData[origin] = {
                coords: ev.clusters[0].coords || [31.0, 35.0], // Fallback if no specific origin_coords
                color: (ev.category && `var(--${ev.category})`) || ev.visual_config?.color || STRATEGIC_METADATA[origin]?.color || tacticalColor
              };
            }
          });
          return Object.entries(originData)
            .filter(([origin]) => {
              const internalTerms = ['Israel', 'terroristInfiltration', 'hostileAircraftIntrusion', 'missiles', 'earthQuake', 'unknown'];
              return !internalTerms.includes(origin);
            })
            .map(([origin, data]) => (
              <Marker
                key={`timeframe-pin-${origin}`}
                position={data.coords}
                icon={L.divIcon({
                  className: 'custom-origin-marker',
                  html: `
                    <div class="origin-wrapper">
                      <div class="origin-label" style="background: ${data.color}">ORIGIN: ${origin.toUpperCase()}</div>
                      <div class="origin-pin" style="background: ${data.color}4D; box-shadow: 0 0 10px ${data.color}"></div>
                    </div>
                  `,
                  iconSize: [100, 50], iconAnchor: [50, 25]
                })}
              >
                <Popup>Launch Origin: {origin}</Popup>
              </Marker>
            ));
        })()}

        {/* Render ALL active events simultaneously */}
        {renderableEvents.map((currentEvent, eventIdx) => (
          <ThreatOverlay
            key={currentEvent?.id || `event-${eventIdx}`}
            event={currentEvent}
            eventKey={currentEvent?.id || `event-${eventIdx}`}
            viewMode={viewMode}
            tacticalColor={tacticalColor}
            highlightColor={highlightColor}
          />
        ))}
      </MapContainer>
    </div>
  );
}
