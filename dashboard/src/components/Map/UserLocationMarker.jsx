import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { useTactical } from '../../context/TacticalContext';
import { isLocationInIsrael } from '../../utils/israelBounds';

const AVATAR_SPRITE_PX = 32;

function createUserLocationIcon() {
  const half = AVATAR_SPRITE_PX / 2;
  return L.divIcon({
    className: 'leaflet-div-icon user-location-marker',
    html: `<div class="user-location-wrap">
      <div class="user-location-avatar" aria-hidden="true"></div>
    </div>`,
    iconSize: [AVATAR_SPRITE_PX, AVATAR_SPRITE_PX],
    iconAnchor: [half, half],
  });
}

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
      icon={createUserLocationIcon()}
    >
      <Popup>Your location</Popup>
    </Marker>
  );
}
