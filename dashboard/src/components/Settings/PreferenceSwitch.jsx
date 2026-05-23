import React from 'react';

export default function PreferenceSwitch({
  id,
  checked,
  disabled,
  onChange,
  label,
  describedBy,
}) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={checked}
      aria-labelledby={describedBy ? undefined : `${id}-label`}
      aria-describedby={describedBy}
      disabled={disabled}
      className={`pref-switch ${checked ? 'pref-switch--on' : ''}`}
      onClick={() => !disabled && onChange(!checked)}
    >
      <span className="pref-switch__track" aria-hidden="true">
        <span className="pref-switch__thumb" />
      </span>
      <span className="visually-hidden">{label}</span>
    </button>
  );
}
