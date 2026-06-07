import L from 'leaflet';

let svgPathRenderer;

/**
 * Single bearing source for map motion sprites (missile, interceptor, drone).
 * atan2(dx, -dy): angle clockwise from screen up; same convention as CSS rotate().
 */
export function screenBearingBetween(map, p1, p2) {
  const a = map.latLngToLayerPoint(L.latLng(p1[0], p1[1]));
  const b = map.latLngToLayerPoint(L.latLng(p2[0], p2[1]));
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) return 0;
  const deg = (Math.atan2(dx, -dy) * 180) / Math.PI;
  return (deg + 360) % 360;
}

/** SVG renderer so CSS stroke-dash animations work (canvas ignores them). */
export function getSvgPathRenderer() {
  if (!svgPathRenderer) {
    svgPathRenderer = L.svg({ padding: 0.5 });
  }
  return svgPathRenderer;
}

/** Origin label + pin; anchor at pin center so trajectory line meets the ring. */
export const ORIGIN_MARKER_ICON_WIDTH = 100;
export const ORIGIN_MARKER_ICON_HEIGHT = 40;
export const ORIGIN_MARKER_ICON_ANCHOR = [50, 36];

export function buildOriginMarkerIcon(origin, color) {
  return L.divIcon({
    className: 'custom-origin-marker',
    html: `
      <div class="origin-wrapper">
        <div class="origin-label" style="background: ${color}">ORIGIN: ${origin.toUpperCase()}</div>
        <div class="origin-pin" style="background: ${color}4D; box-shadow: 0 0 10px ${color}"></div>
      </div>
    `,
    iconSize: [ORIGIN_MARKER_ICON_WIDTH, ORIGIN_MARKER_ICON_HEIGHT],
    iconAnchor: ORIGIN_MARKER_ICON_ANCHOR,
  });
}
