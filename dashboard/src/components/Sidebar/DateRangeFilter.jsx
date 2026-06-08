import React from 'react';

export default function DateRangeFilter({ timeFrame, onTimeFrameChange }) {
  const rangeParts = timeFrame.startsWith('range:')
    ? timeFrame.split(':')[1].split(',')
    : ['', ''];
  const fromValue = rangeParts[0] ?? '';
  const toValue = rangeParts[1] ?? '';

  return (
    <div className="date-range-filter">
      <span className="date-range-filter__label">FROM:</span>
      <input
        type="date"
        className="date-range-filter__input"
        aria-label="From date"
        value={fromValue}
        onChange={(e) => {
          onTimeFrameChange(`range:${e.target.value},${toValue}`);
        }}
      />
      <span className="date-range-filter__label">TO:</span>
      <input
        type="date"
        className="date-range-filter__input"
        aria-label="To date"
        value={toValue}
        onChange={(e) => {
          onTimeFrameChange(`range:${fromValue},${e.target.value}`);
        }}
      />
    </div>
  );
}
