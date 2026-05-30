import { useEffect, useMemo, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  DRONE_SPEED_MPS,
  closeWaypointPath,
  haversineMeters,
  motionSpeedMps,
  roundCoordKey,
} from '../../utils/trajectoryPaths';
import { getSvgPathRenderer } from '../../utils/mapRenderers';

const SVG_PATH_RENDERER = getSvgPathRenderer();
const MIN_LEG_MS = 800;
const MOTION_Z_INDEX = 2500;

function droneScaleForZoom(zoom) {
  const baseZoom = 12;
  const geoScale = 2 ** (zoom - baseZoom);
  return Math.min(Math.max(geoScale, 0.25), 1.2);
}

function createDroneIcon(color, scale, bearing) {
  const hex = color?.startsWith?.('#') ? color : '#ff9500';
  return L.divIcon({
    className: 'drone-tracker-marker',
    html: `<div class="drone-container" style="transform: translate(-50%, -50%) rotate(${bearing}deg) scale(${scale}); --threat-color: ${hex};">
             <div class="drone-tail"></div>
             <div class="drone-body-premium"></div>
           </div>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

function legDurationMs(p1, p2, zoom, speedMps = DRONE_SPEED_MPS) {
  const meters = haversineMeters(p1, p2);
  if (meters <= 0) return MIN_LEG_MS;
  const midLat = (p1[0] + p2[0]) / 2;
  const geoSec = Math.max(meters / speedMps, 0.25);
  const effectiveMps = motionSpeedMps(speedMps, zoom, midLat, meters, geoSec);
  return Math.max(MIN_LEG_MS, (meters / effectiveMps) * 1000);
}

function waypointPathKey(waypoints) {
  return waypoints?.map((p) => roundCoordKey(p[0], p[1])).join('|') ?? '';
}

/**
 * Imperative drone patrol along city waypoints (closed loop). No per-frame React state.
 */
export default function TrackingDrone({ positions, color }) {
  const map = useMap();
  const positionsRef = useRef(positions);
  positionsRef.current = positions;
  const colorRef = useRef(color);
  colorRef.current = color;

  const pathKey = waypointPathKey(positions);
  const closedPath = useMemo(
    () => closeWaypointPath(positions ?? []),
    [pathKey],
  );

  useEffect(() => {
    const pts = positionsRef.current;
    if (!pts?.length) return undefined;

    const resolveHex = () => (
      colorRef.current?.startsWith?.('#') ? colorRef.current : '#ff9500'
    );
    let hex = resolveHex();
    let marker = null;
    let polyline = null;
    let rafId = 0;

    const syncDroneIcon = (bearing, zoom) => {
      if (!marker) return;
      const scale = droneScaleForZoom(zoom);
      marker.setIcon(createDroneIcon(hex, scale, bearing));
    };

    if (pts.length === 1) {
      const zoom = map.getZoom();
      marker = L.marker(pts[0], {
        icon: createDroneIcon(hex, droneScaleForZoom(zoom), 0),
        interactive: false,
        zIndexOffset: MOTION_Z_INDEX,
      }).addTo(map);
      const onZoom = () => syncDroneIcon(0, map.getZoom());
      map.on('zoomend', onZoom);
      return () => {
        map.off('zoomend', onZoom);
        marker?.remove();
      };
    }

    if (pts.length < 2) return undefined;

    const zoom = map.getZoom();
    const pathWeight = Math.max(1, 2 * (zoom / 12));
    polyline = L.polyline(closedPath, {
      renderer: SVG_PATH_RENDERER,
      color: hex,
      weight: pathWeight,
      dashArray: '5, 10',
      opacity: 0.5,
      className: 'drone-path-line',
      interactive: false,
    }).addTo(map);

    marker = L.marker(pts[0], {
      icon: createDroneIcon(hex, droneScaleForZoom(zoom), 0),
      interactive: false,
      zIndexOffset: MOTION_Z_INDEX,
    }).addTo(map);

    let idx = 0;
    let legStart = performance.now();
    let legDuration = legDurationMs(pts[0], pts[1], zoom);
    let lastBearing = 0;

    const onZoom = () => {
      const z = map.getZoom();
      hex = resolveHex();
      polyline?.setStyle({
        color: hex,
        weight: Math.max(1, 2 * (z / 12)),
      });
      const p1 = pts[idx];
      const p2 = pts[(idx + 1) % pts.length];
      legDuration = legDurationMs(p1, p2, z);
      syncDroneIcon(lastBearing, z);
    };
    map.on('zoomend', onZoom);

    const tick = (now) => {
      if (typeof document !== 'undefined' && document.hidden) {
        legStart = now;
        rafId = requestAnimationFrame(tick);
        return;
      }

      const z = map.getZoom();
      let elapsed = now - legStart;
      while (elapsed >= legDuration) {
        elapsed -= legDuration;
        idx = (idx + 1) % pts.length;
        const p1 = pts[idx];
        const p2 = pts[(idx + 1) % pts.length];
        legDuration = legDurationMs(p1, p2, z);
        legStart = now - elapsed;
      }

      const p1 = pts[idx];
      const p2 = pts[(idx + 1) % pts.length];
      const t = legDuration > 0 ? elapsed / legDuration : 0;
      const lat = p1[0] + (p2[0] - p1[0]) * t;
      const lng = p1[1] + (p2[1] - p1[1]) * t;
      const dx = p2[1] - p1[1];
      const dyScreen = -(p2[0] - p1[0]);
      const bearing = (Math.atan2(dyScreen, dx) * 180) / Math.PI;

      marker.setLatLng([lat, lng]);
      if (Math.abs(bearing - lastBearing) >= 8) {
        lastBearing = bearing;
        syncDroneIcon(bearing, z);
      }

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafId);
      map.off('zoomend', onZoom);
      polyline?.remove();
      marker?.remove();
    };
  }, [map, pathKey, closedPath, color]);

  return null;
}
