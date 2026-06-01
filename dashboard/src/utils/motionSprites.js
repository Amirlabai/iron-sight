import { motionSpriteTransformCss } from './trajectoryPaths';

export function getMotionSpriteEl(marker, className) {
  const root = typeof marker?.getElement === 'function' ? marker.getElement() : marker?._icon;
  if (!root) return null;
  if (root.classList?.contains(className)) return root;
  return root.querySelector?.(`.${className}`) ?? null;
}

export function applyMotionSpriteBearing(marker, className, screenBearing, options = {}) {
  const el = getMotionSpriteEl(marker, className);
  if (!el) return false;
  const transform = motionSpriteTransformCss(screenBearing, options);
  if (el.dataset.motionTransform === transform) return true;
  el.dataset.motionTransform = transform;
  el.dataset.bearing = String(screenBearing);
  el.style.transform = transform;
  return true;
}
