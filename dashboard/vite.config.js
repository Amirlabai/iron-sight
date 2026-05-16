import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'fs'
import path from 'path'

const versionData = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../version.json'), 'utf-8'))

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      registerType: 'autoUpdate',
      injectRegister: 'script-defer',
      includeAssets: ['favicon.png', 'favicon.svg', 'icons.svg'],
      manifest: {
        short_name: "Iron Sight",
        name: "Iron Sight Communication System",
        icons: [
          {
            src: "icon-192.png",
            type: "image/png",
            sizes: "192x192"
          },
          {
            src: "icon-512.png",
            type: "image/png",
            sizes: "512x512"
          }
        ],
        start_url: "/?utm_source=pwa",
        background_color: "#ffffff",
        theme_color: "#000000",
        display: "standalone",
        orientation: "portrait"
      },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,mp3}']
      }
    })
  ],
  define: {
    __APP_VERSION__: JSON.stringify(versionData.version)
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/ws': {
        target: 'http://localhost:8080',
        ws: true,
        changeOrigin: true
      }
    }
  }
})
