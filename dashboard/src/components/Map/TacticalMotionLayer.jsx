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
} from '../../utils/trajectoryPaths';
import { applyMotionSpriteBearing } from '../../utils/motionSprites';
import {
  TacticalMotionContext,
  MAX_MISSILE_INSTANCES,
} from './TacticalMotionContext';
import { screenBearingBetween } from '../../utils/mapRenderers';

export { useTacticalMotion } from './TacticalMotionContext';
export { MAX_MISSILE_INSTANCES } from './TacticalMotionContext';

const MOTION_Z_INDEX = 2500;
const EXPLOSION_BURST_MS = 700;
const MEET_REACHED_FRACTION = 0.995;
const MISSILE_SPRITE_PX = 64;
const INTERCEPTOR_SPRITE_PX = 20;

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
    html: `<div class="motion-sprite-wrap" style="--threat-color: ${hex}">
             <div class="missile-sprite"></div>
           </div>`,
    iconSize: [MISSILE_SPRITE_PX, MISSILE_SPRITE_PX],
    iconAnchor: [half, half],
  });
}

function createInterceptorIcon() {
  const half = INTERCEPTOR_SPRITE_PX / 2;
  return L.divIcon({
    className: 'leaflet-div-icon tactical-motion-marker interceptor-sprite-marker',
    html: `<div class="motion-sprite-wrap">
             <div class="interceptor-sprite"></div>
           </div>`,
    iconSize: [INTERCEPTOR_SPRITE_PX, INTERCEPTOR_SPRITE_PX],
    iconAnchor: [half, half],
  });
}

const EXPLOSION_ICON_PX = 64;

function createExplosionIcon() {
  const half = EXPLOSION_ICON_PX / 2;
  return L.divIcon({
    className: 'leaflet-div-icon tactical-motion-marker intercept-explosion-marker',
    html: `<div class="intercept-explosion-wrap">
      <div class="intercept-kill">
        <div class="intercept-kill-flash"></div>
        <div class="intercept-kill-shockwave"></div>
        <div class="intercept-kill-core"></div>
      </div>
    </div>`,
    iconSize: [EXPLOSION_ICON_PX, EXPLOSION_ICON_PX],
    iconAnchor: [half, half],
  });
}

/** Centroid of visible engagement markers (inbound + interceptors) at kill time. */
function interceptBurstLatLng(inst) {
  const pts = [];
  const main = inst.main?.getLatLng?.();
  if (main) pts.push([main.lat, main.lng]);
  inst.interceptors?.forEach((m) => {
    if (!m || m.getOpacity?.() === 0) return;
    const ll = m.getLatLng?.();
    if (ll) pts.push([ll.lat, ll.lng]);
  });
  if (!pts.length) return inst.plan.meetPoint;
  if (pts.length === 1) return pts[0];
  let lat = 0;
  let lng = 0;
  for (const p of pts) {
    lat += p[0];
    lng += p[1];
  }
  return [lat / pts.length, lng / pts.length];
}

function snapMissileEngagementToMeet(inst) {
  const mp = inst.plan.meetPoint;
  inst.main.setLatLng(mp);
  inst.interceptors.forEach((m) => m.setLatLng(mp));
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
  inst.lastInterceptorBearings = inst.interceptors.map(() => null);
}

function enterMissileHold(inst, now) {
  if (inst.state === 'hold') return;
  const holdNow = now ?? (typeof performance !== 'undefined' ? performance.now() : Date.now());
  // Sample while sprites are still visible (before opacity 0).
  const burstAt = interceptBurstLatLng(inst);
  inst.state = 'hold';
  inst.holdStart = holdNow;
  inst.main.setOpacity(0);
  inst.interceptors.forEach((m) => m.setOpacity(0));
  if (!inst.explosion) {
    inst.explosion = L.marker(burstAt, {
      icon: createExplosionIcon(),
      opacity: 1,
      ...motionMarkerOptions({ zIndexOffset: MOTION_Z_INDEX + 200 }),
    }).addTo(inst.map);
    updateExplosionBurst(inst, holdNow);
  } else {
    inst.explosion.setLatLng(burstAt);
  }
}

function screenTangentBearing(map, path, cumDist, distance) {
  const pos = positionAtArcDistance(path, cumDist, distance);
  if (!pos) return null;

  const total = cumDist[cumDist.length - 1];
  if (total <= 0) return 0;

  const eps = Math.max(80, total * 0.03);
  if (distance + eps < total) {
    const ahead = positionAtArcDistance(path, cumDist, distance + eps);
    return screenBearingBetween(map, pos, ahead);
  }
  if (distance > eps) {
    const behind = positionAtArcDistance(path, cumDist, distance - eps);
    return screenBearingBetween(map, behind, pos);
  }
  const ahead = positionAtArcDistance(path, cumDist, Math.min(eps, total));
  return screenBearingBetween(map, pos, ahead);
}

function applyMissileBearing(marker, screenBearing) {
  applyMotionSpriteBearing(marker, 'missile-sprite', screenBearing);
}

function applyInterceptorBearing(marker, screenBearing) {
  applyMotionSpriteBearing(marker, 'interceptor-sprite', screenBearing);
}

function scheduleReapplySpriteBearing(inst) {
  requestAnimationFrame(() => {
    if (inst.lastMainBearing != null) {
      applyMissileBearing(inst.main, inst.lastMainBearing);
    }
    inst.lastInterceptorBearings?.forEach((bearing, i) => {
      const marker = inst.interceptors[i];
      if (marker && bearing != null) applyInterceptorBearing(marker, bearing);
    });
  });
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
    lastMainBearing: null,
    lastInterceptorBearings: [],
  };

  attachMissileInterceptors(map, inst);
  inst.lastInterceptorBearings = inst.interceptors.map(() => null);
  const bearing0 = screenTangentBearing(map, plan.mainPathToMeet, plan.cumDistMain, 0);
  if (bearing0 != null) {
    inst.lastMainBearing = bearing0;
    applyMissileBearing(main, bearing0);
  }
  return inst;
}

function destroyMissileInstance(inst) {
  inst.main.remove();
  inst.interceptors.forEach((m) => m.remove());
  removeExplosion(inst);
}

function updateMissileInbound(inst, dt, mapZoom, now) {
  const { plan, map } = inst;
  const lat = plan.mainPathToMeet[0][0];
  const inboundSec = Math.max(plan.mainTimeToMeet, MIN_MISSILE_LOOP_MS / 1000);
  const speed = motionSpeedMps(plan.speedMps, mapZoom, lat, plan.mainArcM, inboundSec);

  inst.loopElapsed += dt;
  const dMain = Math.min(inst.loopElapsed * speed, plan.mainArcM);
  const mainPos = positionAtArcDistance(plan.mainPathToMeet, plan.cumDistMain, dMain);

  if (mainPos) {
    inst.main.setLatLng(mainPos);
    inst.main.setOpacity(1);
    const bearing = screenTangentBearing(map, plan.mainPathToMeet, plan.cumDistMain, dMain);
    if (bearing != null) {
      inst.lastMainBearing = bearing;
      applyMissileBearing(inst.main, bearing);
    }
  }

  attachMissileInterceptors(map, inst);
  if (!inst.lastInterceptorBearings?.length) {
    inst.lastInterceptorBearings = inst.interceptors.map(() => null);
  }
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
      const bearing = screenTangentBearing(map, path, plan.cumDistInt[i], dInt);
      if (bearing != null) {
        inst.lastInterceptorBearings[i] = bearing;
        applyInterceptorBearing(marker, bearing);
      }
    }
  });

  const reachedMeet = inst.loopElapsed >= inboundSec * MEET_REACHED_FRACTION
    || (plan.mainArcM > 0 && dMain >= plan.mainArcM * MEET_REACHED_FRACTION);
  if (reachedMeet) {
    snapMissileEngagementToMeet(inst);
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
  const bearing0 = screenTangentBearing(
    inst.map,
    inst.plan.mainPathToMeet,
    inst.plan.cumDistMain,
    0,
  );
  if (bearing0 != null) {
    inst.lastMainBearing = bearing0;
    applyMissileBearing(inst.main, bearing0);
  }
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
      scheduleReapplySpriteBearing(existing);
      if (existing.state === 'hold') {
        existing.explosion?.setLatLng(interceptBurstLatLng(existing));
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
    scheduleReapplySpriteBearing(inst);
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
