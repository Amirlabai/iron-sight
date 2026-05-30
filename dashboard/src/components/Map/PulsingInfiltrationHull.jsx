import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { getSvgPathRenderer } from '../../utils/mapRenderers';

const PULSE_PERIOD_MS = 1400;

function shouldAnimatePulse(pulse) {
  if (!pulse) return false;
  if (typeof document !== 'undefined' && document.hidden) return false;
  if (typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return false;
  }
  return true;
}

function positionsKey(positions) {
  if (!positions?.length) return '';
  const ringKey = (ring) => ring.map((p) => `${p[0]},${p[1]}`).join(';');
  if (Array.isArray(positions[0]?.[0])) {
    return positions.map(ringKey).join('|');
  }
  return ringKey(positions);
}

/**
 * Infiltration city hull with rAF-driven fill/stroke pulse (CSS fails on Leaflet SVG attrs).
 */
export function PulsingInfiltrationHull({ positions, color, pulse, tooltip }) {
  const map = useMap();
  const key = positionsKey(positions);

  useEffect(() => {
    if (!positions?.length || !color) return undefined;

    const renderer = getSvgPathRenderer();
    const halo = L.polygon(positions, {
      renderer,
      color,
      weight: 12,
      opacity: 0.12,
      fill: false,
      smoothFactor: 1.5,
      lineJoin: 'round',
      lineCap: 'round',
    }).addTo(map);

    const fill = L.polygon(positions, {
      renderer,
      fillColor: color,
      fillOpacity: 0.28,
      color,
      weight: 2.5,
      smoothFactor: 1.5,
      lineJoin: 'round',
      lineCap: 'round',
      className: 'organic-hull infiltration-city-hull',
    }).addTo(map);

    if (tooltip) {
      fill.bindTooltip(tooltip, { sticky: true });
    }

    let rafId = 0;
    if (shouldAnimatePulse(pulse)) {
      const start = performance.now();
      const tick = (now) => {
        if (typeof document !== 'undefined' && document.hidden) {
          rafId = requestAnimationFrame(tick);
          return;
        }
        const phase = ((now - start) % PULSE_PERIOD_MS) / PULSE_PERIOD_MS;
        const wave = 0.5 + 0.5 * Math.sin(phase * Math.PI * 2);
        fill.setStyle({
          fillOpacity: 0.12 + 0.42 * wave,
          opacity: 0.35 + 0.65 * wave,
        });
        halo.setStyle({ opacity: 0.06 + 0.16 * wave });
        rafId = requestAnimationFrame(tick);
      };
      rafId = requestAnimationFrame(tick);
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      map.removeLayer(halo);
      map.removeLayer(fill);
    };
  }, [map, key, color, pulse, tooltip]);

  return null;
}

export function PulsingInfiltrationCircle({ center, radius, color, pulse, tooltip }) {
  const map = useMap();
  const key = `${center[0]},${center[1]}|${radius}|${color}`;

  useEffect(() => {
    if (!center || !color) return undefined;

    const renderer = getSvgPathRenderer();
    const ring = L.circle(center, {
      renderer,
      radius,
      color,
      weight: 2,
      fillColor: color,
      fillOpacity: 0.25,
      className: 'infiltration-city-hull',
    }).addTo(map);

    if (tooltip) {
      ring.bindTooltip(tooltip, { permanent: true, direction: 'center', className: 'city-boundary-label' });
    }

    let rafId = 0;
    if (shouldAnimatePulse(pulse)) {
      const start = performance.now();
      const tick = (now) => {
        if (typeof document !== 'undefined' && document.hidden) {
          rafId = requestAnimationFrame(tick);
          return;
        }
        const phase = ((now - start) % PULSE_PERIOD_MS) / PULSE_PERIOD_MS;
        const wave = 0.5 + 0.5 * Math.sin(phase * Math.PI * 2);
        ring.setStyle({
          fillOpacity: 0.1 + 0.35 * wave,
          opacity: 0.4 + 0.6 * wave,
        });
        rafId = requestAnimationFrame(tick);
      };
      rafId = requestAnimationFrame(tick);
    }

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      map.removeLayer(ring);
    };
  }, [map, key, center, radius, color, pulse, tooltip]);

  return null;
}
