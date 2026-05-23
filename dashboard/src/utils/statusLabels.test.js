import { describe, expect, it } from 'vitest';
import {
  getLiveStatusPillAriaLabel,
  getLiveStatusPillLabel,
  getSandboxStatusPillLabel,
} from './statusLabels';

describe('statusLabels', () => {
  it('uses short mobile copy', () => {
    expect(getLiveStatusPillLabel(true, { status: 'OPERATIONAL', source: 'LIVE' }, { compact: true })).toBe('LIVE');
    expect(getLiveStatusPillLabel(false, {}, { compact: true })).toBe('RECONNECTING');
    expect(getLiveStatusPillLabel(true, { status: 'DEGRADED', source: 'X' }, { compact: true })).toBe('DEGRADED');
    expect(getSandboxStatusPillLabel({ compact: true })).toBe('SANDBOX');
  });

  it('uses full desktop copy', () => {
    expect(getLiveStatusPillLabel(true, { status: 'OPERATIONAL', source: 'PIKUD' }, { compact: false })).toBe(
      'LIVE INTERCEPT: PIKUD',
    );
    expect(getLiveStatusPillAriaLabel(true, { status: 'OPERATIONAL', source: 'PIKUD' })).toBe('LIVE INTERCEPT: PIKUD');
  });
});
