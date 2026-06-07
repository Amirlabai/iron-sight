import { describe, it, expect, beforeEach } from 'vitest';
import {
  getWsReconnectDelayMs,
  WS_RECONNECT_MAX_MS,
  consumeWsReconnectDelayMs,
  resetWsFailStreak,
  _getWsFailStreakForTests,
  _setWsFailStreakForTests,
} from './wsReconnect';

describe('getWsReconnectDelayMs', () => {
  it('waits 3s for the first three failures then doubles', () => {
    expect(getWsReconnectDelayMs(0)).toBe(3000);
    expect(getWsReconnectDelayMs(1)).toBe(3000);
    expect(getWsReconnectDelayMs(2)).toBe(3000);
    expect(getWsReconnectDelayMs(3)).toBe(6000);
    expect(getWsReconnectDelayMs(4)).toBe(12000);
    expect(getWsReconnectDelayMs(5)).toBe(24000);
  });

  it('caps at WS_RECONNECT_MAX_MS', () => {
    expect(getWsReconnectDelayMs(10)).toBe(WS_RECONNECT_MAX_MS);
  });

  it('treats negative fail count as zero', () => {
    expect(getWsReconnectDelayMs(-1)).toBe(3000);
  });
});

describe('consumeWsReconnectDelayMs', () => {
  beforeEach(() => {
    resetWsFailStreak();
  });

  it('returns flat 3s delays then backoff and increments streak', () => {
    expect(consumeWsReconnectDelayMs()).toBe(3000);
    expect(_getWsFailStreakForTests()).toBe(1);
    expect(consumeWsReconnectDelayMs()).toBe(3000);
    expect(_getWsFailStreakForTests()).toBe(2);
    expect(consumeWsReconnectDelayMs()).toBe(3000);
    expect(_getWsFailStreakForTests()).toBe(3);
    expect(consumeWsReconnectDelayMs()).toBe(6000);
    expect(_getWsFailStreakForTests()).toBe(4);
  });

  it('resetWsFailStreak restarts sequence', () => {
    consumeWsReconnectDelayMs();
    consumeWsReconnectDelayMs();
    resetWsFailStreak();
    expect(consumeWsReconnectDelayMs()).toBe(3000);
    _setWsFailStreakForTests(0);
  });
});
