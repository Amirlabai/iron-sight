import { createContext, useContext } from 'react';

export const TacticalMotionContext = createContext(null);

export const MAX_MISSILE_INSTANCES = 8;

const noop = () => {};

export function useTacticalMotion() {
  const ctx = useContext(TacticalMotionContext);
  if (!ctx) {
    return {
      registerMissile: noop,
      patchMissile: noop,
      unregister: noop,
    };
  }
  return ctx;
}
