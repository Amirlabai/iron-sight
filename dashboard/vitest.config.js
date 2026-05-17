import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      leaflet: path.resolve(dir, 'src/test-utils/leaflet-mock.js'),
      'leaflet/dist/images/marker-icon.png': path.resolve(dir, 'src/test-utils/asset-mock.js'),
      'leaflet/dist/images/marker-shadow.png': path.resolve(dir, 'src/test-utils/asset-mock.js'),
    },
  },
  test: {
    environment: 'node',
  },
});
