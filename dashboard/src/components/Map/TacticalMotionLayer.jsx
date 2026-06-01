import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  HOLD_MS,
  MIN_MISSILE_LOOP_MS,
  motionSpeedMps,
  positionAtArcDistance,
  positionAndBearingAtDistance,
} from '../../utils/trajectoryPaths';
import {
  TacticalMotionContext,
  MAX_MISSILE_INSTANCES,
} from './TacticalMotionContext';

export { useTacticalMotion } from './TacticalMotionContext';
export { MAX_MISSILE_INSTANCES } from './TacticalMotionContext';

const MOTION_Z_INDEX = 2500;
const EXPLOSION_BURST_MS = 700;
const MEET_REACHED_FRACTION = 0.995;
/** Pixel art faces NE; path bearing 0° = east. */
const MISSILE_SPRITE_BEARING_OFFSET = -45;
const MISSILE_SPRITE_PX = 32;

function getMarkerElement(marker) {
  if (!marker) return null;
  if (typeof marker.getElement === 'function') {
    const el = marker.getElement();
    if (el) return el;
  }
  return marker._icon ?? null;
}

function createMissileIcon(color) {
  const hex = color?.startsWith?.('#') ? color : '#ff3b30';
  const half = MISSILE_SPRITE_PX / 2;
  return L.divIcon({
    className: 'leaflet-div-icon tactical-motion-marker missile-sprite-marker',
    html: `<div class="missile-sprite" style="--threat-color: ${hex}"></div>`,
    iconSize: [MISSILE_SPRITE_PX, MISSILE_SPRITE_PX],
    iconAnchor: [half, half],
  });
}

function createInterceptorIcon() {
  return L.divIcon({
    className: 'leaflet-div-icon tactical-motion-marker interceptor-sprite-marker',
    html: '<div class="interceptor-sprite"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function createExplosionIcon() {
  return L.divIcon({
    className: 'leaflet-div-icon tactical-motion-marker intercept-explosion-marker',
    html: `<div class="intercept-kill">
      <div class="intercept-kill-flash"></div>
      <div class="intercept-kill-shockwave"></div>
      <div class="intercept-kill-core"></div>
    </div>`,
    iconSize: [64, 64],
    iconAnchor: [32, 32],
  });
}

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3;
}

function removeExplosion(inst) {
  inst.explosion?.remove();
  inst.explosion = null;
}

/** Small local burst at meet point (imperative; matches animations.css). */
function updateExplosionBurst(inst, now) {
  if (!inst.explosion) return;
  const elapsed = now - inst.holdStart;
  const t = Math.min(elapsed / EXPLOSION_BURST_MS, 1);
  const ease = easeOutCubic(t);
  const root = getMarkerElement(inst.explosion)?.querySelector('.intercept-kill');
  if (!root) return;

  const flash = root.querySelector('.intercept-kill-flash');
  const shock = root.querySelector('.intercept-kill-shockwave');
  const core = root.querySelector('.intercept-kill-core');

  const flashScale = 0.45 + 1.35 * ease;
  const flashOpacity = t < 0.12 ? 1 : Math.max(0, 1 - (t - 0.12) / 0.5);

  const shockScale = 0.3 + 1.5 * ease;
  const shockOpacity = Math.max(0, 0.95 - t * 1.1);

  const coreScale = 0.4 + 1.1 * ease;
  const coreOpacity = Math.max(0, 1 - t * 0.9);

  if (flash) {
    flash.style.opacity = String(flashOpacity);
    flash.style.transform = `translate(-50%, -50%) scale(${flashScale})`;
  }
  if (shock) {
    shock.style.opacity = String(shockOpacity);
    shock.style.transform = `translate(-50%, -50%) scale(${shockScale})`;
  }
  if (core) {
    core.style.opacity = String(coreOpacity);
    core.style.transform = `translate(-50%, -50%) scale(${coreScale})`;
  }

  inst.explosion.setOpacity(1);
}

function motionMarkerOptions(extra = {}) {
  return {
    interactive: false,
    zIndexOffset: MOTION_Z_INDEX,
    ...extra,
  };
}

function interceptorMarkerOptions() {
  return motionMarkerOptions({ zIndexOffset: MOTION_Z_INDEX + 50 });
}

function refreshMissileInterceptors(inst) {
  inst.interceptors.forEach((m) => m.remove());
  inst.interceptors = [];
  attachMissileInterceptors(inst.map, inst);
}

function enterMissileHold(inst, now) {
  if (inst.state === 'hold') return;
  const holdNow = now ?? (typeof performance !== 'undefined' ? performance.now() : Date.now());
  inst.state = 'hold';
  inst.holdStart = holdNow;
  inst.main.setOpacity(0);
  inst.interceptors.forEach((m) => m.setOpacity(0));
  if (!inst.explosion) {
    inst.explosion = L.marker(inst.plan.meetPoint, {
      icon: createExplosionIcon(),
      opacity: 1,
      ...motionMarkerOptions({ zIndexOffset: MOTION_Z_INDEX + 200 }),
    }).addTo(inst.map);
    updateExplosionBurst(inst, holdNow);
  }
}

function applySpriteBearing(marker, bearing, { flip = false, sprite = 'missile' } = {}) {
  const selector = sprite === 'interceptor' ? '.interceptor-sprite' : '.missile-sprite';
  const el = getMarkerElement(marker)?.querySelector(selector);
  if (!el) return;
  const offset = sprite === 'missile' ? MISSILE_SPRITE_BEARING_OFFSET : 0;
  const deg = (flip ? bearing + 180 : bearing) + offset;
  const prev = el.dataset.bearing;
  if (prev !== undefined && Math.abs(Number(prev) - deg) < 8) return;
  el.dataset.bearing = String(deg);
  el.style.transform = `translate(-50%, -50%) rotate(${deg}deg)`;
}

function attachMissileInterceptors(map, inst) {
  if (inst.interceptors?.length) return;
  inst.interceptors = inst.plan.interceptorPaths.map(() =>
    L.marker(inst.plan.meetPoint, {
      icon: createInterceptorIcon(),
      opacity: 0,
      ...interceptorMarkerOptions(),
    }).addTo(map),
  );
}

function createMissileInstance(map, id, { plan, color, planKey, loopElapsed = 0 }) {
  const start = plan.mainPathToMeet[0];
  const main = L.marker(start, {
    icon: createMissileIcon(color),
    ...motionMarkerOptions(),
  }).addTo(map);

  const inst = {
    type: 'missile',
    id,
    plan,
    color,
    map,
    main,
    interceptors: [],
    explosion: null,
    state: 'inbound',
    planKey,
    loopElapsed,
    holdStart: 0,
  };

  attachMissileInterceptors(map, inst);
  return inst;
}

function destroyMissileInstance(inst) {
  inst.main.remove();
  inst.interceptors.forEach((m) => m.remove());
  removeExplosion(inst);
}

function updateMissileInbound(inst, dt, mapZoom, now) {
  const { plan } = inst;
  const lat = plan.mainPathToMeet[0][0];
  const inboundSec = Math.max(plan.mainTimeToMeet, MIN_MISSILE_LOOP_MS / 1000);
  const speed = motionSpeedMps(plan.speedMps, mapZoom, lat, plan.mainArcM, inboundSec);

  inst.loopElapsed += dt;
  const dMain = Math.min(inst.loopElapsed * speed, plan.mainArcM);
  const mainPos = positionAtArcDistance(plan.mainPathToMeet, plan.cumDistMain, dMain);

  if (mainPos) {
    inst.main.setLatLng(mainPos);
    inst.main.setOpacity(1);
    const info = positionAndBearingAtDistance(plan.mainPathToMeet, plan.cumDistMain, dMain);
    if (info) applySpriteBearing(inst.main, info.bearing);
  }

  attachMissileInterceptors(inst.map, inst);
  plan.interceptorPaths.forEach((path, i) => {
    const marker = inst.interceptors[i];
    if (!marker) return;
    const intArc = Math.min(plan.intArcM[i], plan.mainArcM);
    const startMainD = Math.max(0, plan.mainArcM - intArc);
    if (dMain < startMainD) {
      marker.setOpacity(0);
      return;
    }
    const dInt = Math.min(dMain - startMainD, intArc);
    const pos = positionAtArcDistance(path, plan.cumDistInt[i], dInt);
    if (pos) {
      marker.setLatLng(pos);
      marker.setOpacity(1);
      const info = positionAndBearingAtDistance(path, plan.cumDistInt[i], dInt);
      if (info) applySpriteBearing(marker, info.bearing, { sprite: 'interceptor' });
    }
  });

  const reachedMeet = inst.loopElapsed >= inboundSec * MEET_REACHED_FRACTION
    || (plan.mainArcM > 0 && dMain >= plan.mainArcM * MEET_REACHED_FRACTION);
  if (reachedMeet) {
    enterMissileHold(inst, now);
  }
}

function resetMissileInstance(inst) {
  removeExplosion(inst);
  inst.state = 'inbound';
  inst.loopElapsed = 0;
  inst.main.setOpacity(1);
  inst.interceptors.forEach((m) => m.setOpacity(0));
  inst.main.setLatLng(inst.plan.mainPathToMeet[0]);
}

export function TacticalMotionProvider({ children }) {
  const map = useMap();
  const missilesRef = useRef(new Map());
  const rafRef = useRef(0);
  const lastTimeRef = useRef(0);
  const registerGenRef = useRef(new Map());

  const upsertMissile = useCallback((id, payload) => {
    const existing = missilesRef.current.get(id);
    if (existing) {
      const geometryChanged = existing.planKey !== payload.planKey;
      existing.planKey = payload.planKey;
      existing.color = payload.color;
      existing.plan = payload.plan;
      existing.main.setIcon(createMissileIcon(payload.color));
      if (existing.state === 'hold') {
        existing.explosion?.setLatLng(payload.plan.meetPoint);
        return;
      }
      if (geometryChanged) {
        refreshMissileInterceptors(existing);
      }
      return;
    }
    if (missilesRef.current.size >= MAX_MISSILE_INSTANCES) {
      const firstKey = missilesRef.current.keys().next().value;
      if (firstKey && firstKey !== id) {
        destroyMissileInstance(missilesRef.current.get(firstKey));
        missilesRef.current.delete(firstKey);
      }
    }
    missilesRef.current.set(id, createMissileInstance(map, id, payload));
  }, [map]);

  const patchMissile = useCallback((id, { color }) => {
    const inst = missilesRef.current.get(id);
    if (!inst || !color) return;
    inst.color = color;
    inst.main.setIcon(createMissileIcon(color));
  }, []);

  const registerMissile = useCallback((id, payload) => {
    if (!payload?.plan || !payload?.planKey) return;
    const gen = (registerGenRef.current.get(id) ?? 0) + 1;
    registerGenRef.current.set(id, gen);
    const apply = () => {
      if (registerGenRef.current.get(id) !== gen) return;
      upsertMissile(id, payload);
    };
    if (map._loaded) apply();
    else map.whenReady(apply);
  }, [map, upsertMissile]);

  const unregister = useCallback((id) => {
    registerGenRef.current.delete(id);
    if (missilesRef.current.has(id)) {
      destroyMissileInstance(missilesRef.current.get(id));
      missilesRef.current.delete(id);
    }
  }, []);

  const motionApiRef = useRef({ registerMissile, patchMissile, unregister });
  motionApiRef.current = { registerMissile, patchMissile, unregister };

  const contextValue = useMemo(
    () => ({
      registerMissile: (id, p) => motionApiRef.current.registerMissile(id, p),
      patchMissile: (id, p) => motionApiRef.current.patchMissile(id, p),
      unregister: (id) => motionApiRef.current.unregister(id),
    }),
    [],
  );

  useEffect(() => {
    const missiles = missilesRef.current;
    return () => {
      missiles.forEach(destroyMissileInstance);
      missiles.clear();
      registerGenRef.current.clear();
    };
  }, [map]);

  useEffect(() => {
    const tick = (now) => {
      rafRef.current = requestAnimationFrame(tick);
      if (typeof document !== 'undefined' && document.hidden) {
        lastTimeRef.current = now;
        return;
      }

      if (!lastTimeRef.current) {
        lastTimeRef.current = now;
        return;
      }
      const dt = Math.min((now - lastTimeRef.current) / 1000, 0.1);
      lastTimeRef.current = now;
      if (dt <= 0) return;

      const zoom = map.getZoom();

      missilesRef.current.forEach((inst) => {
        if (inst.state === 'hold') {
          updateExplosionBurst(inst, now);
          const holdMs = Math.max(HOLD_MS, EXPLOSION_BURST_MS + 120);
          if (now - inst.holdStart >= holdMs) {
            resetMissileInstance(inst);
          }
          return;
        }
        updateMissileInbound(inst, dt, zoom, now);
      });
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [map]);

  return (
    <TacticalMotionContext.Provider value={contextValue}>
      {children}
    </TacticalMotionContext.Provider>
  );
}
