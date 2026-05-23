import React from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, useMap, useMapEvents, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  ISRAEL_CENTER,
  DEFAULT_ZOOM,
  TACTICAL_BOUNDARIES,
  STRATEGIC_METADATA,
  MOBILE_LAYOUT_BREAKPOINT,
  getBoundaryHoles,
  getBoundaryOuter,
} from '../../utils/constants';
import { getFitPadding, boundsKey, resolveOriginPinCoords } from '../../utils/mapGeometry';
import { useTactical } from '../../context/TacticalContext';
import { formatTime } from '../../utils/formatters';
import ThreatOverlay from './ThreatOverlay';

function refitMap(map, { center, zoom, bounds, maxZoom }) {
  if (bounds?.length >= 2) {
    const latLngBounds = L.latLngBounds(bounds.map(([lat, lng]) => [lat, lng]));
    map.fitBounds(latLngBounds, {
      ...getFitPadding(),
      maxZoom: maxZoom ?? (window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT ? 10 : 12),
      duration: 0,
    });
    return;
  }
  map.flyTo(center, zoom, { duration: 0 });
}

function MapController({ center, zoom, bounds, maxZoom }) {
  const map = useMap();
  const prevRef = React.useRef('');
  const bKey = boundsKey(bounds);
  const configRef = React.useRef({ center, zoom, bounds, maxZoom });
  configRef.current = { center, zoom, bounds, maxZoom };

  React.useEffect(() => {
    const key = bounds?.length >= 2
      ? `bounds:${bKey}:${maxZoom ?? ''}`
      : `fly:${center[0]},${center[1]},${zoom}`;

    if (key === prevRef.current) return;
    prevRef.current = key;

    if (bounds?.length >= 2) {
      const latLngBounds = L.latLngBounds(bounds.map(([lat, lng]) => [lat, lng]));
      map.fitBounds(latLngBounds, {
        ...getFitPadding(),
        maxZoom: maxZoom ?? (window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT ? 10 : 12),
        duration: 0.8,
      });
      return;
    }

    map.flyTo(center, zoom, { duration: 0.6 });
  }, [center, zoom, bounds, bKey, maxZoom, map]);

  React.useEffect(() => {
    const onResize = () => {
      map.invalidateSize();
      refitMap(map, configRef.current);
    };
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
    };
  }, [map]);

  return null;
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: () => onMapClick(),
  });
  return null;
}

function IsraelBaseLayer() {
  const israelBoundary = TACTICAL_BOUNDARIES['Israel'];
  const israelColor = STRATEGIC_METADATA['Israel']?.color || '#ffffff';
  const holeStroke = '#8ec5ff';
  const holes = getBoundaryHoles(israelBoundary);

  return (
    <>
      <Polygon
        key="israel-base-layer"
        positions={israelBoundary}
        pathOptions={{
          color: israelColor,
          weight: 2,
          fill: true,
          fillColor: israelColor,
          fillOpacity: 0.005,
          smoothFactor: 1.0,
          className: 'israel-border-static',
        }}
      />
      {holes.map((ring, i) => (
        <Polygon
          key={`israel-hole-stroke-${i}`}
          positions={ring}
          pathOptions={{
            color: holeStroke,
            weight: 2,
            fill: false,
            interactive: false,
          }}
        />
      ))}
    </>
  );
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

        <MapController
          center={mapConfig.center}
          zoom={mapConfig.zoom}
          bounds={mapConfig.bounds}
          maxZoom={mapConfig.maxZoom}
        />
        <ZoomControl position="bottomright" />
        <MapClickHandler onMapClick={() => {
          if (window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT) setIsSidebarExpanded(false);
        }} />

        <IsraelBaseLayer />

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
            const outer = getBoundaryOuter(boundary);
            const color = STRATEGIC_METADATA[origin]?.color || tacticalColor;
            if (!outer?.length) return null;
            return (
              <React.Fragment key={`timeframe-origin-${origin}`}>
                <Polygon positions={outer} pathOptions={{ color, weight: 15, opacity: 0.05, fill: false, className: 'origin-threat-halo' }} />
                <Polygon positions={outer} pathOptions={{ fillColor: color, fillOpacity: 0.1, color, weight: 1, className: 'origin-threat-glow' }} />
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
                const coords = resolveOriginPinCoords(t.origin, t);
                if (!coords) return;
                originData[t.origin] = {
                  coords,
                  color: (ev.category && `var(--${ev.category})`) || ev.visual_config?.color || STRATEGIC_METADATA[t.origin]?.color || tacticalColor
                };
              }
            });
            ev.highlight_origins?.forEach(o => {
              if (!originData[o.name]) {
                const coords = resolveOriginPinCoords(o.name, { marker_coords: o.coords, origin_coords: o.coords });
                if (!coords) return;
                originData[o.name] = {
                  coords,
                  color: STRATEGIC_METADATA[o.name]?.color || tacticalColor
                };
              }
            });
            if (ev.clusters?.[0]?.origin && !originData[ev.clusters[0].origin]) {
              const origin = ev.clusters[0].origin;
              const traj = ev.trajectories?.find(tr => tr.origin === origin);
              const coords = resolveOriginPinCoords(origin, traj);
              if (!coords) return;
              originData[origin] = {
                coords,
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
