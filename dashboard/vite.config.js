import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const versionData = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../version.json'), 'utf-8'))
const isBuild = process.argv.includes('build')
/** Legal pages only — do not prerender / (SPA dashboard DOM differs; stale index + SW caused black screen). */
const PRERENDER_ROUTES = ['/about', '/accessibility', '/privacy', '/terms']

/** vite-prerender + injectManifest can leave timers open; Node never exits (local + Vercel hang). */
function forceExitAfterBuild() {
  return {
    name: 'force-exit-after-build',
    apply: 'build',
    enforce: 'post',
    closeBundle: {
      sequential: true,
      order: 'post',
      handler() {
        setTimeout(() => process.exit(0), 250)
      },
    },
  }
}

async function loadPlugins() {
  const plugins = [react()]
  const prerenderEnabled = isBuild && process.env.PRERENDER !== '0'
  if (prerenderEnabled) {
    const { vitePrerenderPlugin } = await import('vite-prerender-plugin')
    plugins.push(
      vitePrerenderPlugin({
        renderTarget: '#root',
        prerenderScript: path.resolve(__dirname, 'src/prerender.jsx'),
        additionalPrerenderRoutes: PRERENDER_ROUTES,
      }),
    )
  }
  plugins.push(
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      registerType: 'autoUpdate',
      injectRegister: null,
      includeAssets: ['favicon.png', 'favicon.svg', 'icons.svg', 'og-image.png', 'sprites/rocket.png'],
      manifest: {
        short_name: 'Iron Sight',
        name: 'Iron Sight — Live Israel Alert Map',
        description:
          'Real-time tactical map for Israel civil defense alerts, rockets, drones, and airspace monitoring.',
        lang: 'en',
        categories: ['utilities', 'news'],
        icons: [
          {
            src: 'icon-192.png',
            type: 'image/png',
            sizes: '192x192',
          },
          {
            src: 'icon-512.png',
            type: 'image/png',
            sizes: '512x512',
          },
        ],
        start_url: '/?utm_source=pwa',
        background_color: '#0a0a0c',
        theme_color: '#0a0a0c',
        display: 'standalone',
        orientation: 'any',
      },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,mp3}'],
        sourcemap: false,
      },
    }),
  )
  if (prerenderEnabled) {
    plugins.push(forceExitAfterBuild())
  }
  return plugins
}

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: await loadPlugins(),
  define: {
    __APP_VERSION__: JSON.stringify(versionData.version),
  },
  build: {
    sourcemap: false,
  },
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
    },
  },
}))
