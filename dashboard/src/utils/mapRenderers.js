import L from 'leaflet';

let svgPathRenderer;

/** SVG renderer so CSS stroke-dash animations work (canvas ignores them). */
export function getSvgPathRenderer() {
  if (!svgPathRenderer) {
    svgPathRenderer = L.svg({ padding: 0.5 });
  }
  return svgPathRenderer;
}
