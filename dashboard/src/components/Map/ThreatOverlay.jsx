import React, { useMemo } from 'react';
import { Circle, Polyline, Marker, Popup, Polygon, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import { TACTICAL_BOUNDARIES, STRATEGIC_METADATA, getBoundaryOuter } from '../../utils/constants';
import { resolveCanvasColor, resolveMarkerColor } from '../../utils/mapColors';
import { getSvgPathRenderer, buildOriginMarkerIcon } from '../../utils/mapRenderers';
import { normalizeDroneWaypoints, resolveMissileEndpoints, trajectoriesForDisplay } from '../../utils/motionEndpoints';
import { MissileMotionRegistrar } from './MotionRegistrars';
import TrackingDrone from './TrackingDrone';
import { PulsingInfiltrationCircle, PulsingInfiltrationHull } from './PulsingInfiltrationHull';
import OriginHaloPolygons from './OriginHaloPolygons';

const CITY_LABEL_MIN_ZOOM = 11;
const LIVE_CITY_LABEL_CAP = 12;
const CITY_FALLBACK_RADIUS_METERS = 500;

const SVG_PATH_RENDERER = getSvgPathRenderer();

export default function ThreatOverlay({
  event,
  eventKey,
  viewMode,
  tacticalColor,
  highlightColor,
  mapZoom = 0,
  suppressCityDetail = false,
}) {
  const isLive = viewMode === 'live';

  const animatedPathOptions = useMemo(
    () => ({ renderer: SVG_PATH_RENDERER }),
    [],
  );

  if (!event) return null;

  const isNewsFlash = event.category === 'newsFlash';
  const isInfiltration = event.category === 'terroristInfiltration';
  const isEarthquake = event.category === 'earthQuake';
  const liveClusterAnimClass = isLive && !isNewsFlash
    ? (isEarthquake ? 'pulse-animation' : (event.visual_config?.movement || 'pulse-animation'))
    : '';
  const clusterHaloClass = isNewsFlash ? 'organic-hull' : 'organic-hull origin-threat-halo';

  return (
    <React.Fragment>
      {/* Clusters */}
      {event.clusters?.map((cluster, idx) => {
        const clusterColor = resolveCanvasColor(event, tacticalColor, cluster);
        const iconColor = resolveMarkerColor(event, tacticalColor, cluster);
        const movement = event.visual_config?.movement;
        const rawDroneCoords = cluster.cities?.map((c) => c.coords).filter((c) => c && c.length >= 2) ?? [];
        const dronePositions = normalizeDroneWaypoints(rawDroneCoords, cluster.centroid);
        const primaryCity = cluster.cities?.[0];
        const infiltrationOutline = isInfiltration && primaryCity?.boundary
          && getBoundaryOuter(primaryCity.boundary).length >= 3
          ? primaryCity.boundary
          : null;
        const earthquakeHasCityBoundary = isEarthquake && primaryCity?.boundary
          && getBoundaryOuter(primaryCity.boundary).length >= 3;

        return (
          <React.Fragment key={`${eventKey}-cluster-${idx}`}>
            {infiltrationOutline ? (
              <PulsingInfiltrationHull
                positions={infiltrationOutline}
                color={clusterColor}
                pulse={isLive}
                tooltip={primaryCity?.name || 'Infiltration Alert'}
              />
            ) : cluster.hull && cluster.hull.length > 2 && !isInfiltration && !earthquakeHasCityBoundary ? (
              <React.Fragment>
                <Polygon
                  positions={cluster.hull}
                  pathOptions={{
                    color: clusterColor, weight: 15, opacity: 0.1, fill: false,
                    smoothFactor: 2.0, lineJoin: 'round', lineCap: 'round',
                    className: clusterHaloClass
                  }}
                />
                <Polygon
                  positions={cluster.hull}
                  pathOptions={{
                    fillColor: clusterColor, fillOpacity: 0.3, color: clusterColor,
                    weight: 3, smoothFactor: 2.0, lineJoin: 'round', lineCap: 'round',
                    className: `organic-hull ${liveClusterAnimClass}`
                  }}
                >
                  <Tooltip sticky>Threat Area: {cluster.cities?.length || 0} Targets</Tooltip>
                </Polygon>
              </React.Fragment>
            ) : cluster.centroid && !isInfiltration && !earthquakeHasCityBoundary ? (
              <React.Fragment>
                <Circle center={cluster.centroid} radius={2000}
                  pathOptions={{ color: clusterColor, weight: 12, opacity: 0.1, fill: false, className: isNewsFlash ? '' : 'origin-threat-halo' }}
                />
                <Circle center={cluster.centroid} radius={2000}
                  pathOptions={{
                    fillColor: clusterColor, fillOpacity: 0.4, color: clusterColor, weight: 2,
                    className: liveClusterAnimClass
                  }}
                />
              </React.Fragment>
            ) : null}
            {!suppressCityDetail && cluster.cities?.map((city, cityIdx) => {
              if (!city?.coords) return null;
              const shouldMountLabel = mapZoom >= CITY_LABEL_MIN_ZOOM
                && (viewMode !== 'live' || cityIdx < LIVE_CITY_LABEL_CAP);
              const cityKey = `${eventKey}-cluster-${idx}-city-${city.city_id || city.name || cityIdx}`;
              const cityOuter = city?.boundary ? getBoundaryOuter(city.boundary) : null;
              const hasCityOutline = cityOuter && cityOuter.length >= 3;

              if (isInfiltration && hasCityOutline) {
                if (!shouldMountLabel) return null;
                return (
                  <Polygon
                    key={`${cityKey}-label`}
                    positions={city.boundary}
                    pathOptions={{
                      color: clusterColor,
                      weight: 0,
                      opacity: 0,
                      fill: false,
                      fillOpacity: 0,
                      interactive: false,
                    }}
                  >
                    <Tooltip permanent direction="center" className="city-boundary-label">
                      {city.name}
                    </Tooltip>
                  </Polygon>
                );
              }

              if (isEarthquake && hasCityOutline) {
                return (
                  <Polygon
                    key={cityKey}
                    positions={city.boundary}
                    pathOptions={{
                      fillColor: clusterColor,
                      fillOpacity: 0.3,
                      color: clusterColor,
                      weight: 2,
                      opacity: 0.85,
                      smoothFactor: 1.5,
                      lineJoin: 'round',
                      lineCap: 'round',
                      className: `organic-hull earthquake-city-hull ${liveClusterAnimClass}`,
                      interactive: false,
                    }}
                  >
                    {shouldMountLabel ? (
                      <Tooltip permanent direction="center" className="city-boundary-label">
                        {city.name}
                      </Tooltip>
                    ) : null}
                  </Polygon>
                );
              }

              if (!hasCityOutline) {
                if (isInfiltration) {
                  return (
                    <PulsingInfiltrationCircle
                      key={cityKey}
                      center={city.coords}
                      radius={CITY_FALLBACK_RADIUS_METERS}
                      color={clusterColor}
                      pulse={isLive}
                      tooltip={shouldMountLabel ? city.name : undefined}
                    />
                  );
                }
                if (isEarthquake) {
                  return (
                    <Circle
                      key={cityKey}
                      center={city.coords}
                      radius={CITY_FALLBACK_RADIUS_METERS}
                      pathOptions={{
                        fillColor: clusterColor,
                        fillOpacity: 0.35,
                        color: clusterColor,
                        weight: 2,
                        className: liveClusterAnimClass,
                        interactive: false,
                      }}
                    >
                      {shouldMountLabel ? (
                        <Tooltip permanent direction="center" className="city-boundary-label">
                          {city.name}
                        </Tooltip>
                      ) : null}
                    </Circle>
                  );
                }
                return (
                  <Circle
                    key={cityKey}
                    center={city.coords}
                    radius={CITY_FALLBACK_RADIUS_METERS}
                    pathOptions={{
                      color: clusterColor,
                      weight: 1.5,
                      opacity: 0.85,
                      fill: false,
                      interactive: false,
                    }}
                  >
                    {shouldMountLabel ? (
                      <Tooltip
                        permanent
                        direction="center"
                        className="city-boundary-label"
                      >
                        {city.name}
                      </Tooltip>
                    ) : null}
                  </Circle>
                );
              }
              return (
                <Polygon
                  key={cityKey}
                  positions={city.boundary}
                  pathOptions={{
                    color: clusterColor,
                    weight: 1.5,
                    opacity: 0.85,
                    fill: false,
                    lineJoin: 'round',
                    lineCap: 'round',
                    interactive: false,
                  }}
                >
                  {shouldMountLabel ? (
                    <Tooltip
                      permanent
                      direction="center"
                      className="city-boundary-label"
                    >
                      {city.name}
                    </Tooltip>
                  ) : null}
                </Polygon>
              );
            })}
            {isLive && movement === 'circular_sweep' && dronePositions.length >= 2 ? (
              <TrackingDrone positions={dronePositions} color={iconColor} />
            ) : null}
            {isLive && !isNewsFlash && !isInfiltration && !isEarthquake && event.visual_config && movement !== 'linear' && movement !== 'circular_sweep' && (() => {
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
      {trajectoriesForDisplay(event).map((traj, idx) => {
        const trajColor = resolveCanvasColor(event, tacticalColor, traj);
        const iconColor = resolveMarkerColor(event, tacticalColor, traj);
        const boundary = TACTICAL_BOUNDARIES[traj.origin];
        const motionEndpoints = resolveMissileEndpoints(traj, event);
        const hasLine = Boolean(motionEndpoints);
        const showMissileMotion = isLive
          && event.category === 'missiles'
          && motionEndpoints;

        return (
          <React.Fragment key={`${eventKey}-traj-${idx}`}>
            {boundary && viewMode !== 'timeframe' && (
              <OriginHaloPolygons
                positions={getBoundaryOuter(boundary)}
                color={trajColor}
              />
            )}

            {hasLine && viewMode !== 'timeframe' && (
              <React.Fragment>
                <Polyline
                  positions={[motionEndpoints.origin, motionEndpoints.target]}
                  pathOptions={{
                    color: trajColor,
                    weight: 10,
                    opacity: 0.1,
                    smoothFactor: 2.0,
                    className: 'trajectory-halo',
                  }}
                />
                <Polyline
                  positions={[motionEndpoints.origin, motionEndpoints.target]}
                  pathOptions={{
                    ...animatedPathOptions,
                    color: trajColor,
                    weight: 2,
                    dashArray: '10, 10',
                    smoothFactor: 2.0,
                    className: isLive && event.category === 'missiles' ? 'missile-path-line' : 'trajectory-line',
                  }}
                />
              </React.Fragment>
            )}
            {showMissileMotion ? (
              <MissileMotionRegistrar
                id={`${eventKey}-traj-${idx}-motion`}
                origin={motionEndpoints.origin}
                target={motionEndpoints.target}
                color={iconColor}
                enabled
              />
            ) : null}
            {viewMode !== 'timeframe' && motionEndpoints?.origin && (
              <Marker
                position={motionEndpoints.origin}
                icon={buildOriginMarkerIcon(traj.origin, trajColor)}
              >
                <Popup>Launch Origin: {traj.origin}</Popup>
              </Marker>
            )}
          </React.Fragment>
        );
      })}

      {/* Legacy Origin Highlights (Standalone) */}
      {viewMode !== 'timeframe' && event.highlight_origins?.map((org, idx) => (
        <React.Fragment key={`${eventKey}-highlight-${idx}`}>
          {TACTICAL_BOUNDARIES[org.name] ? (
            <OriginHaloPolygons
              positions={getBoundaryOuter(TACTICAL_BOUNDARIES[org.name])}
              color={STRATEGIC_METADATA[org.name]?.color || highlightColor}
            />
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
