import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Polygon, useMap } from 'react-leaflet';
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import { ISRAEL_CENTER, DEFAULT_ZOOM } from '../../utils/constants';
import { TACTICAL_BOUNDARIES } from '../../utils/tactical_geodata';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

function coloredIcon(color) {
  return L.divIcon({
    className: 'replay-marker',
    html: `<span style="background:${color};width:12px;height:12px;border-radius:50%;display:block;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.5)"></span>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function MapFitter({ visuals }) {
  const map = useMap();

  useEffect(() => {
    const points = [];
    (visuals?.markers || []).forEach((m) => points.push([m.lat, m.lon]));
    (visuals?.polylines || []).forEach((pl) => {
      (pl.points || []).forEach((p) => points.push(p));
    });
    (visuals?.polygons || []).forEach((poly) => {
      (poly.rings || []).flat().forEach((p) => points.push(p));
    });
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], DEFAULT_ZOOM);
      return;
    }
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 10 });
  }, [visuals, map]);

  return null;
}

function BaseTerritories() {
  return (
    <>
      {Object.entries(TACTICAL_BOUNDARIES).map(([name, ring]) => (
        <Polygon
          key={name}
          positions={ring}
          pathOptions={{
            color: name === 'Israel' ? '#444' : '#666',
            weight: 1,
            fillOpacity: name === 'Israel' ? 0.03 : 0,
            dashArray: name === 'Israel' ? undefined : '4 4',
          }}
        />
      ))}
    </>
  );
}

export default function ReplayMap({ step }) {
  const visuals = step?.visuals || {};

  return (
    <div className="replay-map">
      <MapContainer center={ISRAEL_CENTER} zoom={DEFAULT_ZOOM} className="leaflet-root">
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <BaseTerritories />
        <MapFitter visuals={visuals} />

        {(visuals.polygons || []).map((poly, i) =>
          (poly.rings || []).map((ring, j) => (
            <Polygon
              key={`poly-${i}-${j}`}
              positions={ring}
              pathOptions={{
                color: poly.color || '#4d94ff',
                fillColor: poly.color || '#4d94ff',
                fillOpacity: poly.fillOpacity ?? 0.15,
                weight: 2,
              }}
            />
          ))
        )}

        {(visuals.polylines || []).map((pl, i) => (
          <Polyline
            key={`line-${i}`}
            positions={pl.points || []}
            pathOptions={{
              color: pl.color || '#4d94ff',
              weight: 3,
              dashArray: pl.dashed ? '8 8' : undefined,
            }}
          />
        ))}

        {(visuals.markers || []).map((m, i) => (
          <Marker
            key={`marker-${i}-${m.label}`}
            position={[m.lat, m.lon]}
            icon={coloredIcon(m.color || '#ff4d4d')}
          >
            {m.label && <Popup>{m.label}</Popup>}
          </Marker>
        ))}

        {(visuals.annotations || []).map((a, i) => (
          <Marker
            key={`ann-${i}`}
            position={[a.lat, a.lon]}
            icon={L.divIcon({
              className: 'replay-annotation',
              html: `<span class="ann-label">${a.text}</span>`,
              iconSize: [0, 0],
              iconAnchor: [0, 0],
            })}
          />
        ))}
      </MapContainer>
    </div>
  );
}
