import { vi } from 'vitest';

vi.mock('leaflet/dist/images/marker-icon.png', () => ({ default: '' }));
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({ default: '' }));

if (typeof globalThis.window === 'undefined') {
  globalThis.window = {
    location: {
      host: 'localhost:5173',
      protocol: 'http:',
    },
    innerWidth: 1280,
  };
}
