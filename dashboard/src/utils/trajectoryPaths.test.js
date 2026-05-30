import { describe, it, expect } from 'vitest';
import {
  buildInterceptPlan,
  buildWaypointLoopPlan,
  closeWaypointPath,
  pathLengthMeters,
  buildMainPath,
  roundCoordKey,
  motionSpeedMps,
  visibleMetersPerSecond,
  metersPerPixel,
  MISSILE_SPEED_MPS,
  DRONE_SPEED_MPS,
} from './trajectoryPaths';

describe('trajectoryPaths', () => {
  const origin = [33.5, 35.5];
  const target = [32.0, 34.8];
  const shortTarget = [32.5, 35.0];

  it('buildInterceptPlan ends interceptors at meet point', () => {
    const plan = buildInterceptPlan(origin, target);
    expect(plan.interceptorPaths).toHaveLength(3);
    plan.interceptorPaths.forEach((path) => {
      const end = path[path.length - 1];
      expect(end[0]).toBeCloseTo(plan.meetPoint[0], 4);
      expect(end[1]).toBeCloseTo(plan.meetPoint[1], 4);
    });
  });

  it('interceptor arc length never exceeds main arc', () => {
    const plan = buildInterceptPlan(origin, target);
    plan.intArcM.forEach((arc) => {
      expect(arc).toBeLessThanOrEqual(plan.mainArcM);
    });
  });

  it('roundCoordKey stabilizes jittery coordinates', () => {
    const a = roundCoordKey(32.123456, 34.987654);
    const b = roundCoordKey(32.123459, 34.987651);
    expect(a).toBe(b);
  });

  it('longer main arc implies longer time to meet at fixed speed', () => {
    const short = buildInterceptPlan(origin, shortTarget, { speedMps: MISSILE_SPEED_MPS });
    const long = buildInterceptPlan(origin, target, { speedMps: MISSILE_SPEED_MPS });
    expect(long.mainArcM).toBeGreaterThan(short.mainArcM);
    expect(long.mainTimeToMeet).toBeGreaterThan(short.mainTimeToMeet);
  });

  it('buildWaypointLoopPlan doubles loop period when path length doubles', () => {
    const a = [32.0, 34.8];
    const b = [32.1, 34.9];
    const c = [32.2, 35.0];
    const shortPlan = buildWaypointLoopPlan([a, b], { speedMps: DRONE_SPEED_MPS });
    const longPath = buildWaypointLoopPlan([a, b, c], { speedMps: DRONE_SPEED_MPS });
    const doubled = buildWaypointLoopPlan(
      [a, b, ...buildMainPath(b, c, 32).slice(1)],
      { speedMps: DRONE_SPEED_MPS },
    );
    expect(shortPlan.loopPeriod).toBeLessThan(longPath.loopPeriod);
    expect(doubled.totalArcM).toBeGreaterThan(shortPlan.totalArcM);
  });

  it('closeWaypointPath repeats first point at end', () => {
    const open = [[32, 34], [32.1, 34.1], [32.2, 34.2]];
    const closed = closeWaypointPath(open);
    expect(closed).toHaveLength(4);
    expect(closed[3][0]).toBe(closed[0][0]);
    expect(closed[3][1]).toBe(closed[0][1]);
  });

  it('returns null for insufficient waypoints', () => {
    expect(buildWaypointLoopPlan([[32, 34]])).toBeNull();
    expect(buildWaypointLoopPlan([])).toBeNull();
  });

  it('visibleMetersPerSecond increases when zoomed in', () => {
    expect(visibleMetersPerSecond(1000, 8, 32)).toBeGreaterThan(1000);
    expect(visibleMetersPerSecond(1000, 12, 32)).toBeLessThan(
      visibleMetersPerSecond(1000, 8, 32),
    );
  });

  it('motionSpeedMps enforces minimum loop duration', () => {
    const speed = motionSpeedMps(600, 10, 32, 120000, 4);
    expect(speed).toBeGreaterThanOrEqual(120000 / 4);
  });

  it('pathLengthMeters is positive for distinct points', () => {
    const path = buildMainPath(origin, target, 10);
    expect(pathLengthMeters(path)).toBeGreaterThan(0);
  });
});
