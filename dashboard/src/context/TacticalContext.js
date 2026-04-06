import { createContext, useContext } from 'react';

export const TacticalContext = createContext(null);

export function useTactical() {
  const ctx = useContext(TacticalContext);
  if (!ctx) throw new Error('useTactical must be used within TacticalProvider');
  return ctx;
}
