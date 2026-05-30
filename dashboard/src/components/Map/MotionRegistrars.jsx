import { useEffect, useRef } from 'react';
import { buildInterceptPlan, roundCoordKey } from '../../utils/trajectoryPaths';
import { areMotionEndpointsValid } from '../../utils/motionEndpoints';
import { useTacticalMotion } from './TacticalMotionContext';

function parseCoordKey(key) {
  if (!key) return null;
  const [lat, lng] = key.split(',').map(Number);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return [lat, lng];
}

export function MissileMotionRegistrar({ id, origin, target, color, enabled }) {
  const { registerMissile, patchMissile, unregister } = useTacticalMotion();
  const originKey = origin ? roundCoordKey(origin[0], origin[1]) : '';
  const targetKey = target ? roundCoordKey(target[0], target[1]) : '';
  const planKey = originKey && targetKey ? `${originKey}|${targetKey}` : '';
  const colorRef = useRef(color);
  colorRef.current = color;

  // Unregister only when slot disabled/unmounted — not when live coords refine (planKey change).
  useEffect(() => {
    if (!enabled) return undefined;
    return () => unregister(id);
  }, [id, enabled, unregister]);

  useEffect(() => {
    if (!enabled || !planKey) return;
    const o = parseCoordKey(originKey);
    const t = parseCoordKey(targetKey);
    if (!o || !t || !areMotionEndpointsValid(o, t)) return;
    const plan = buildInterceptPlan(o, t);
    registerMissile(id, { plan, color: colorRef.current, planKey });
  }, [id, planKey, enabled, originKey, targetKey, registerMissile]);

  useEffect(() => {
    if (!enabled || !planKey) return;
    patchMissile(id, { color: colorRef.current });
  }, [id, color, enabled, planKey, patchMissile]);

  return null;
}
