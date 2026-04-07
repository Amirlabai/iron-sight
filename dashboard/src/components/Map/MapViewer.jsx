import React from 'react';
import { MapContainer, TileLayer, Polygon, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { ISRAEL_CENTER, DEFAULT_ZOOM, TACTICAL_BOUNDARIES, STRATEGIC_METADATA } from '../../utils/constants';
import { useTactical } from '../../context/TacticalContext';
import ThreatOverlay from './ThreatOverlay';

function MapController({ center, zoom }) {
  const map = useMap();
  React.useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.5 });
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
        {viewMode === 'archive' && <div className="archive-watermark">HISTORICAL DATA REWIND | {archiveEvent?.time}</div>}
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
