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

export function isVerifiedTrajectory(event) {
  return Boolean(event?.verified || event?.manual_origin);
}

/** Archive map: verified commits use primary trajectory only (legacy rows may have extras). */
export function trajectoriesForDisplay(event) {
  const trajs = event?.trajectories ?? [];
  if (isVerifiedTrajectory(event) && trajs.length > 0) {
    return [trajs[0]];
  }
  return trajs;
}

/** Single origin point for line + pin (tactical display pin; both coord fields kept in sync). */
export function resolveTrajectoryOrigin(traj) {
  if (traj?.origin_coords?.length >= 2) {
    return traj.origin_coords;
  }
  if (traj?.marker_coords?.length >= 2) {
    return traj.marker_coords;
  }
  return null;
}

export function resolveMissileEndpoints(traj, event) {
  const origin = resolveTrajectoryOrigin(traj);

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
