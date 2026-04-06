import React from 'react';
import { Circle, Polyline, Marker, Popup, Polygon, Tooltip, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { TACTICAL_BOUNDARIES, STRATEGIC_METADATA } from '../../utils/constants';

// --- Tracking Drone (Animated Interpolation) ---
const TrackingDrone = ({ positions, color }) => {
  const [currentIdx, setCurrentIdx] = React.useState(0);
  const [progress, setProgress] = React.useState(0);
  const [zoom, setZoom] = React.useState(12);

  const map = useMapEvents({
    zoom() { setZoom(map.getZoom()); }
  });

  React.useEffect(() => {
    if (!positions || positions.length < 2) return;
    let animationFrameId;
    let startTime = Date.now();
    const duration = 2000;

    const animate = () => {
      const now = Date.now();
      const elapsed = now - startTime;
      const p = Math.min(elapsed / duration, 1);
      setProgress(p);
      if (p >= 1) {
        startTime = Date.now();
        setCurrentIdx((prev) => (prev + 1) % positions.length);
      }
      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [positions]);

  if (!positions || positions.length === 0) return null;

  const baseZoom = 12;
  const geoScale = Math.pow(2, zoom - baseZoom);
  const clampedScale = Math.min(Math.max(geoScale, 0.25), 1.2);
  const pathWeight = Math.max(1, 2 * (zoom / 12));

  if (positions.length === 1) {
    return (
      <Marker position={positions[0]} icon={L.divIcon({
        className: 'drone-tracker-marker',
        html: `<div class="drone-container" style="--threat-color: ${color}; transform: translate(-50%, -50%) scale(${clampedScale});">
                 <div class="drone-body-premium"></div>
               </div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0]
      })} />
    );
  }

  const p1 = positions[currentIdx];
  const p2 = positions[(currentIdx + 1) % positions.length];
  const lat = p1[0] + (p2[0] - p1[0]) * progress;
  const lng = p1[1] + (p2[1] - p1[1]) * progress;
  const dx = p2[1] - p1[1];
  const dyScreen = -(p2[0] - p1[0]);
  const angle = Math.atan2(dyScreen, dx) * (180 / Math.PI);

  return (
    <React.Fragment>
      <Polyline
        positions={positions}
        pathOptions={{
          color: color,
          weight: pathWeight,
          dashArray: '5, 10',
          opacity: 0.5,
          className: 'trajectory-line'
        }}
      />
      <Marker position={[lat, lng]} icon={L.divIcon({
        className: 'drone-tracker-marker',
        html: `<div class="drone-container" style="transform: translate(-50%, -50%) rotate(${angle}deg) scale(${clampedScale}); --threat-color: ${color};">
                 <div class="drone-tail"></div>
                 <div class="drone-body-premium"></div>
               </div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0]
      })} />
    </React.Fragment>
  );
};

// --- Threat Overlay (renders clusters, trajectories, origin highlights for a single event) ---
export default function ThreatOverlay({ event, eventKey, viewMode, tacticalColor, highlightColor }) {
  if (!event) return null;

  return (
    <React.Fragment>
      {/* Clusters */}
      {event.clusters?.map((cluster, idx) => {
        const clusterColor = event.visual_config?.color || STRATEGIC_METADATA[cluster.origin]?.color || tacticalColor;
        return (
          <React.Fragment key={`${eventKey}-cluster-${idx}`}>
            {cluster.hull && cluster.hull.length > 2 ? (
              <React.Fragment>
                <Polygon
                  positions={cluster.hull}
                  pathOptions={{
                    color: clusterColor, weight: 15, opacity: 0.1, fill: false,
                    smoothFactor: 2.0, lineJoin: 'round', lineCap: 'round',
                    className: 'organic-hull origin-threat-halo'
                  }}
                />
                <Polygon
                  positions={cluster.hull}
                  pathOptions={{
                    fillColor: clusterColor, fillOpacity: 0.3, color: clusterColor,
                    weight: 3, smoothFactor: 2.0, lineJoin: 'round', lineCap: 'round',
                    className: `organic-hull ${viewMode === 'live' ? (event.visual_config?.movement || 'pulse-animation') : ''}`
                  }}
                >
                  <Tooltip sticky>Threat Area: {cluster.cities?.length || 0} Targets</Tooltip>
                </Polygon>
              </React.Fragment>
            ) : cluster.centroid ? (
              <React.Fragment>
                <Circle center={cluster.centroid} radius={2000}
                  pathOptions={{ color: clusterColor, weight: 12, opacity: 0.1, fill: false, className: 'origin-threat-halo' }}
                />
                <Circle center={cluster.centroid} radius={2000}
                  pathOptions={{
                    fillColor: clusterColor, fillOpacity: 0.4, color: clusterColor, weight: 2,
                    className: viewMode === 'live' ? (event.visual_config?.movement || 'pulse-animation') : ''
                  }}
                />
              </React.Fragment>
            ) : null}
            {viewMode === 'live' && event.visual_config && event.visual_config.movement !== 'linear' && (() => {
              const movement = event.visual_config.movement;
              if (movement === 'circular_sweep' && cluster.cities) {
                return <TrackingDrone positions={cluster.cities.map(c => c.coords).filter(c => c)} color={clusterColor} />;
              }
              if (cluster.centroid) {
                return (
                  <Marker position={cluster.centroid} icon={L.divIcon({
                    className: 'tactical-visual-marker',
                    html: `<div class="visual-wrapper ${movement}" style="--threat-color: ${clusterColor}"></div>`,
                    iconSize: [80, 80], iconAnchor: [40, 40]
                  })} />
                );
              }
              return null;
            })()}
          </React.Fragment>
        );
      })}

      {/* Trajectories */}
      {event.trajectories?.map((traj, idx) => {
        const trajColor = event.visual_config?.color || STRATEGIC_METADATA[traj.origin]?.color || tacticalColor;
        const boundary = TACTICAL_BOUNDARIES[traj.origin];
        
        return (
          <React.Fragment key={`${eventKey}-traj-${idx}`}>
            {/* Origin Country Highlight (Restored) */}
            {boundary && (
              <React.Fragment>
                <Polygon positions={boundary}
                  pathOptions={{
                    color: trajColor,
                    weight: 15, opacity: 0.05, fill: false, smoothFactor: 2.0, className: 'origin-threat-halo'
                  }}
                />
                <Polygon positions={boundary}
                  pathOptions={{
                    fillColor: trajColor,
                    fillOpacity: 0.1, color: trajColor,
                    weight: 1, smoothFactor: 2.0, className: 'origin-threat-glow'
                  }}
                />
              </React.Fragment>
            )}

            {traj.origin_coords && traj.target_coords && (
              <React.Fragment>
                <Polyline positions={[traj.origin_coords, traj.target_coords]}
                  pathOptions={{ color: trajColor, weight: 10, opacity: 0.1, smoothFactor: 2.0, className: 'trajectory-halo' }}
                />
                <Polyline positions={[traj.origin_coords, traj.target_coords]}
                  pathOptions={{ color: trajColor, weight: 2, dashArray: '10, 10', smoothFactor: 2.0, className: 'trajectory-line' }}
                />
              </React.Fragment>
            )}
            <Marker
              position={traj.marker_coords || traj.origin_coords || traj.target_coords || ISRAEL_CENTER}
              icon={L.divIcon({
                className: 'custom-origin-marker',
                html: `
                  <div class="origin-wrapper">
                    <div class="origin-label" style="background: ${trajColor}">ORIGIN: ${traj.origin.toUpperCase()}</div>
                    <div class="origin-pin" style="background: ${trajColor}4D; box-shadow: 0 0 10px ${trajColor}"></div>
                  </div>
                `,
                iconSize: [100, 50], iconAnchor: [50, 25]
              })}
            >
              <Popup>Launch Origin: {traj.origin}</Popup>
            </Marker>
          </React.Fragment>
        );
      })}

      {/* Legacy Origin Highlights (Standalone) */}
      {event.highlight_origins?.map((org, idx) => (
        <React.Fragment key={`${eventKey}-highlight-${idx}`}>
          {TACTICAL_BOUNDARIES[org.name] ? (
            <React.Fragment>
              <Polygon positions={TACTICAL_BOUNDARIES[org.name]}
                pathOptions={{
                  color: STRATEGIC_METADATA[org.name]?.color || highlightColor,
                  weight: 15, opacity: 0.05, fill: false, smoothFactor: 2.0, className: 'origin-threat-halo'
                }}
              />
              <Polygon positions={TACTICAL_BOUNDARIES[org.name]}
                pathOptions={{
                  fillColor: STRATEGIC_METADATA[org.name]?.color || highlightColor,
                  fillOpacity: 0.1, color: STRATEGIC_METADATA[org.name]?.color || highlightColor,
                  weight: 1, smoothFactor: 2.0, className: 'origin-threat-glow'
                }}
              />
            </React.Fragment>
          ) : (
            <React.Fragment>
              <Circle center={org.coords} radius={40000}
                pathOptions={{ color: highlightColor, weight: 20, opacity: 0.05, fill: false, className: 'origin-threat-halo' }}
              />
              <Circle center={org.coords} radius={40000}
                pathOptions={{ fillColor: highlightColor, fillOpacity: 0.1, color: highlightColor, weight: 1, className: 'origin-threat-glow' }}
              />
            </React.Fragment>
          )}
        </React.Fragment>
      ))}

    </React.Fragment>
  );
}
