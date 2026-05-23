import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { useTactical } from '../../context/TacticalContext';
import { isLocationInIsrael } from '../../utils/israelBounds';

export default function UserLocationMarker() {
  const { alertPrefs } = useTactical();
  const loc = alertPrefs?.location;
  const geoOk = alertPrefs?.geoPermission === 'granted';
  const showPin = alertPrefs?.showUserLocationOnMap !== false;

  if (!showPin || !geoOk || !loc || loc.length < 2) return null;
  if (!isLocationInIsrael(loc)) return null;

  return (
    <Marker
      position={loc}
      zIndexOffset={1000}
      icon={L.divIcon({
        className: 'user-location-marker',
        html: '<div class="user-location-dot" aria-hidden="true"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      })}
    >
      <Popup>Your location</Popup>
    </Marker>
  );
}
