import React, { useCallback, useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, useMap, useMapEvents, ZoomControl } from 'react-leaflet';
import { Crosshair } from 'lucide-react';
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
import { TacticalMotionProvider } from './TacticalMotionLayer';
import UserLocationMarker from './UserLocationMarker';
import { agentDebugBurst, agentDebugLog, MAP_RESIZE_BURST } from '../../utils/agentDebugLog';
import { buildOriginMarkerIcon } from '../../utils/mapRenderers';

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

function markProgrammaticMove(map, suppressRef) {
  suppressRef.current = true;
  map.once('moveend', () => {
    suppressRef.current = false;
  });
}

function MapController({ center, zoom, bounds, maxZoom, followAuto, suppressRef }) {
  const map = useMap();
  const prevRef = useRef('');
  const bKey = boundsKey(bounds);
  const configRef = useRef({ center, zoom, bounds, maxZoom });
  configRef.current = { center, zoom, bounds, maxZoom };

  useEffect(() => {
    if (!followAuto) return;

    const key = bounds?.length >= 2
      ? `bounds:${bKey}:${maxZoom ?? ''}`
      : `fly:${center[0]},${center[1]},${zoom}`;

    if (key === prevRef.current) return;
    prevRef.current = key;

    markProgrammaticMove(map, suppressRef);

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
  }, [center, zoom, bounds, bKey, maxZoom, map, followAuto, suppressRef]);

  useEffect(() => {
    let raf = 0;
    const syncSize = (refit = false) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        map.invalidateSize({ pan: false });
        if (refit) {
          markProgrammaticMove(map, suppressRef);
          refitMap(map, configRef.current);
        }
      });
    };

    const onWindowResize = () => {
      // #region agent log
      agentDebugBurst(
        'map-resize',
        'MapViewer.jsx:onResize',
        'map invalidateSize+refit burst',
        { innerW: window.innerWidth },
        'B',
        MAP_RESIZE_BURST.threshold,
        MAP_RESIZE_BURST.windowMs,
      );
      // #endregion
      syncSize(true);
    };

    const wrapper = map.getContainer()?.parentElement;
    const ro = typeof ResizeObserver !== 'undefined' && wrapper
      ? new ResizeObserver(() => syncSize(false))
      : null;
    ro?.observe(wrapper);

    const vv = window.visualViewport;
    const onVisualViewport = () => syncSize(false);
    vv?.addEventListener('resize', onVisualViewport);
    vv?.addEventListener('scroll', onVisualViewport);

    window.addEventListener('resize', onWindowResize);
    window.addEventListener('orientationchange', onWindowResize);
    syncSize(true);
    const t2 = requestAnimationFrame(() => syncSize(false));

    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(t2);
      ro?.disconnect();
      vv?.removeEventListener('resize', onVisualViewport);
      vv?.removeEventListener('scroll', onVisualViewport);
      window.removeEventListener('resize', onWindowResize);
      window.removeEventListener('orientationchange', onWindowResize);
    };
  }, [map, suppressRef]);

  return null;
}

function MapUserMoveTracker({ onUserMove, suppressRef }) {
  useMapEvents({
    dragstart: () => {
      if (!suppressRef.current) onUserMove();
    },
    zoomstart: (e) => {
      if (!suppressRef.current && e.originalEvent) onUserMove();
    },
    wheel: () => {
      if (!suppressRef.current) onUserMove();
    },
  });
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

  // Geodata is static at build time; omit boundary/holes deps intentionally.
  React.useEffect(() => {
    const t0 = performance.now();
    const ringCount = Array.isArray(israelBoundary?.[0]?.[0])
      ? israelBoundary.length
      : 1;
    requestAnimationFrame(() => {
      // #region agent log
      agentDebugLog(
        'MapViewer.jsx:IsraelBaseLayer',
        'Israel layer first frame',
        { ringCount, holeRings: holes.length, scheduleMs: Math.round(performance.now() - t0) },
        'C',
      );
      // #endregion
    });
  }, []);

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
    setIsSidebarExpanded, mapAutoFollowToken, isLightMode,
  } = useTactical();
  const tileUrl = isLightMode
    ? 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png';

  const [mapFollowAuto, setMapFollowAuto] = useState(true);
  const suppressProgrammaticRef = useRef(false);
  const mapRef = useRef(null);
  const mapConfigRef = useRef(mapConfig);
  mapConfigRef.current = mapConfig;

  useEffect(() => {
    setMapFollowAuto(true);
  }, [viewMode, mapAutoFollowToken]);

  const handleUserMovedMap = useCallback(() => {
    setMapFollowAuto(false);
  }, []);

  const handleRecenterMap = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    setMapFollowAuto(true);
    markProgrammaticMove(map, suppressProgrammaticRef);
    refitMap(map, mapConfigRef.current);
  }, []);

  function MapInstanceBridge() {
    const map = useMap();
    useEffect(() => {
      mapRef.current = map;
      return () => {
        if (mapRef.current === map) mapRef.current = null;
      };
    }, [map]);
    return null;
  }

  return (
    <div className="map-wrapper">
      {!mapFollowAuto ? (
        <button
          type="button"
          className="map-recenter-btn"
          onClick={handleRecenterMap}
          aria-label="Center map on current view"
        >
          <Crosshair size={18} aria-hidden="true" />
          <span>Center</span>
        </button>
      ) : null}
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
        <TileLayer url={tileUrl} />

        <MapInstanceBridge />
        <MapController
          center={mapConfig.center}
          zoom={mapConfig.zoom}
          bounds={mapConfig.bounds}
          maxZoom={mapConfig.maxZoom}
          followAuto={mapFollowAuto}
          suppressRef={suppressProgrammaticRef}
        />
        <MapUserMoveTracker
          onUserMove={handleUserMovedMap}
          suppressRef={suppressProgrammaticRef}
        />
        <ZoomControl position="bottomright" />
        <MapClickHandler onMapClick={() => {
          if (window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT) setIsSidebarExpanded(false);
        }} />

        <TacticalMotionProvider>
        <IsraelBaseLayer />
        <UserLocationMarker />

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
                icon={buildOriginMarkerIcon(origin, data.color)}
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
        </TacticalMotionProvider>
      </MapContainer>
    </div>
  );
}
