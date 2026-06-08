import React from 'react';
import { Polygon } from 'react-leaflet';

export default function OriginHaloPolygons({ positions, color, smoothFactor = 2.0 }) {
  if (!positions?.length) return null;
  return (
    <>
      <Polygon
        positions={positions}
        pathOptions={{
          color,
          weight: 15,
          opacity: 0.05,
          fill: false,
          smoothFactor,
          className: 'origin-threat-halo',
        }}
      />
      <Polygon
        positions={positions}
        pathOptions={{
          fillColor: color,
          fillOpacity: 0.1,
          color,
          weight: 1,
          smoothFactor,
          className: 'origin-threat-glow',
        }}
      />
    </>
  );
}
