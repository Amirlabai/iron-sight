import React from 'react';

const dateInputStyle = {
  background: 'rgba(255,255,255,0.08)',
  border: '1px solid var(--border)',
  color: 'white',
  fontSize: '11px',
  padding: '4px 6px',
  width: 'auto',
  minWidth: '105px',
  borderRadius: '4px',
  fontFamily: 'monospace',
};

export default function DateRangeFilter({ timeFrame, onTimeFrameChange }) {
  const rangeParts = timeFrame.startsWith('range:')
    ? timeFrame.split(':')[1].split(',')
    : ['', ''];
  const fromValue = rangeParts[0] ?? '';
  const toValue = rangeParts[1] ?? '';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span style={{ fontSize: '10px', color: 'var(--text-sub)', fontWeight: '600' }}>FROM:</span>
      <input
        type="date"
        style={dateInputStyle}
        value={fromValue}
        onChange={(e) => {
          onTimeFrameChange(`range:${e.target.value},${toValue}`);
        }}
      />
      <span style={{ fontSize: '10px', color: 'var(--text-sub)', fontWeight: '600' }}>TO:</span>
      <input
        type="date"
        style={dateInputStyle}
        value={toValue}
        onChange={(e) => {
          onTimeFrameChange(`range:${fromValue},${e.target.value}`);
        }}
      />
    </div>
  );
}
