/**
 * Resolve motion endpoints when trajectory payloads are partial (merged/live).
 */
import { haversineMeters } from './trajectoryPaths';

/** ~700 m orbit radius for single-city drone patrol */
const ORBIT_DELTA_DEG = 0.006;

const MIN_MOTION_SEPARATION_M = 100;

export function normalizeDroneWaypoints(waypoints, centroid = null) {
  const valid = (waypoints ?? []).filter((c) => c && c.length >= 2).map((c) => [c[0], c[1]]);
  if (valid.length >= 2) return valid;
  if (valid.length === 1) {
    const center = centroid?.length >= 2 ? centroid : valid[0];
    const [lat, lng] = valid[0];
    // Triangle patrol; TrackingDrone closes the loop via index wrap (no duplicate vertex).
    return [
      [lat, lng],
      [center[0] + ORBIT_DELTA_DEG, center[1]],
      [center[0], center[1] + ORBIT_DELTA_DEG],
    ];
  }
  return valid;
}

export function areMotionEndpointsValid(origin, target, minSeparationM = MIN_MOTION_SEPARATION_M) {
  if (!origin || origin.length < 2 || !target || target.length < 2) return false;
  return haversineMeters(origin, target) >= minSeparationM;
}

export function resolveMissileEndpoints(traj, event) {
  if (traj?.origin_coords?.length >= 2 && traj?.target_coords?.length >= 2) {
    if (!areMotionEndpointsValid(traj.origin_coords, traj.target_coords)) return null;
    return { origin: traj.origin_coords, target: traj.target_coords };
  }

  const origin = traj?.origin_coords?.length >= 2
    ? traj.origin_coords
    : traj?.marker_coords?.length >= 2
      ? traj.marker_coords
      : null;

  const target = traj?.target_coords?.length >= 2
    ? traj.target_coords
    : event?.center?.length >= 2
      ? event.center
      : event?.clusters?.[0]?.centroid?.length >= 2
        ? event.clusters[0].centroid
        : null;

  if (origin && target && areMotionEndpointsValid(origin, target)) {
    return { origin, target };
  }
  return null;
}
