import { describe, it, expect } from 'vitest';
import { resolveCanvasColor, resolveMarkerColor } from './mapColors';

describe('mapColors', () => {
  it('returns hex for missiles category (not CSS var)', () => {
    const event = { category: 'missiles' };
    expect(resolveCanvasColor(event, '#888')).toBe('#ff3b30');
    expect(resolveMarkerColor(event, '#888')).toBe('#ff3b30');
  });

  it('returns drone orange for hostile aircraft', () => {
    const event = { category: 'hostileAircraftIntrusion' };
    expect(resolveCanvasColor(event, '#888')).toBe('#ff9500');
  });

  it('prefers visual_config hex', () => {
    const event = { category: 'missiles', visual_config: { color: '#abc123' } };
    expect(resolveCanvasColor(event, '#888')).toBe('#abc123');
  });
});
