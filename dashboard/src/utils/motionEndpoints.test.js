import { describe, it, expect } from 'vitest';
import {
  areMotionEndpointsValid,
  normalizeDroneWaypoints,
  resolveMissileEndpoints,
} from './motionEndpoints';

describe('motionEndpoints', () => {
  it('normalizeDroneWaypoints expands single city into patrol loop', () => {
    const pts = normalizeDroneWaypoints([[32, 34]], [32.01, 34.01]);
    expect(pts).toHaveLength(3);
    expect(pts[0][0]).toBe(32);
    expect(pts[0][0]).not.toBe(pts[1][0]);
  });

  it('rejects endpoints closer than 100m', () => {
    expect(areMotionEndpointsValid([32, 34], [32.0001, 34.0001])).toBe(false);
    expect(resolveMissileEndpoints(
      { origin_coords: [32, 34], target_coords: [32.0001, 34.0001] },
      {},
    )).toBeNull();
  });

  it('resolveMissileEndpoints falls back to event center', () => {
    const traj = { origin_coords: [33, 35], marker_coords: [33, 35] };
    const event = { center: [32, 34.8], clusters: [] };
    const ep = resolveMissileEndpoints(traj, event);
    expect(ep.origin).toEqual([33, 35]);
    expect(ep.target).toEqual([32, 34.8]);
  });

  it('resolveMissileEndpoints prefers origin_coords over legacy marker split', () => {
    const traj = {
      origin_coords: [33.20, 35.28],
      marker_coords: [33.09, 35.64],
      target_coords: [33.08, 35.14],
    };
    const event = { verified: true, manual_origin: 'Lebanon' };
    const ep = resolveMissileEndpoints(traj, event);
    expect(ep.origin).toEqual([33.20, 35.28]);
    expect(ep.target).toEqual([33.08, 35.14]);
  });
});
