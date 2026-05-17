import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));

const assetMock = path.resolve(dir, 'src/test-utils/asset-mock.js');

export default defineConfig({
  resolve: {
    alias: [
      { find: 'leaflet', replacement: path.resolve(dir, 'src/test-utils/leaflet-mock.js') },
      { find: /leaflet\/dist\/images\/.*\.png$/, replacement: assetMock },
    ],
  },
  test: {
    environment: 'node',
    setupFiles: ['./src/test-utils/vitest-setup.js'],
  },
});
