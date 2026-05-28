# Iron Sight — Status

**Updated:** 2026-05-28

## NewsFlash strategic guard follow-up (2026-05-28)

- [x] Refined backend pre-scan in `backend/src/main.py` so strategic mode is enabled only by warning-shaped `newsFlash` payloads (`type == newsFlash` with non-empty `data` or `cities`).
- [x] Added regression test in `backend/tests/test_threat_processor.py` to ensure Lebanon-aligned missile vectors stay `Lebanon` even when `allow_strategic=True`.
- [x] Verified with `backend\\.venv\\Scripts\\python.exe -m pytest tests/test_threat_processor.py` (4 passed).

## Dashboard black screen / build

- [x] **Root cause:** `JsonLdScript` function component inside `<Helmet>` — react-helmet-async v3 throws and React never mounts (empty `#root`). Fixed: inline `<script type="application/ld+json">` in `SEO.jsx`
- [x] Dev networking: use Vite origin in dev so `/api` + `/ws` proxy work (ignore `VITE_WS_URL` when `import.meta.env.DEV`)
- [x] Removed `/` from prerender routes (legal pages only); home stays empty `#root` until SPA mounts
- [x] **Prod splash stuck:** Vercel `/ws` rewrite still serves `index.html` on GET; prod WS now uses `wss://iron-sight-hjwf.onrender.com/ws` directly. Vercel `PRERENDER=0` + no sourcemaps for faster deploys. Confirm live bundle hash after deploy (not stuck on old `index-*.js`)
- [x] Splash: plain DOM overlay; dashboard header/map mount underneath; first-visit alert wizard only (`shouldShowAlertWizard`)
- [x] `prefers-reduced-motion` guard for splash/wizard opacity
- [x] Footer: in-flow on desktop; hidden on mobile (bottom sheet zone)
- [x] Mobile legal nav: header cog menu → About, Accessibility, Privacy, Terms + alert preferences; desktop cog opens preferences panel (not wizard)
- [x] User map pin: blue dot when GPS inside Israel; opt-out in preferences panel (`showUserLocationOnMap`)
- [x] `AlertPreferencesPanel`: toggle rows (notify, location, map pin, map zoom, scope + radius); `israelBounds` + `geoPolygon` utils
- [x] Editable map zoom levels (4–14, commit on blur / close; partial digits revert; reset defaults) and history launch-origin filter (`mapZoomLevels.js`, `historyFilters.js`)
- [x] Map Center button after user pan/zoom; auto-framing pauses until recenter or view mode change
- [x] Fast build: `$env:PRERENDER='0'; npm run build` (~10s). Full SEO prerender: default `npm run build` (4 legal routes; may take longer)

## CSS shell refactor

- [x] Desktop header/sidebar shell layout consolidated in `dashboard/src/styles/layout.css` (≥1025px + ≤1024px)
- [x] `App.css` — component visuals only; `returnLiveFadeIn` in `animations.css`
- [x] `npm run build` (dashboard) passes

## Israel boundary cutout (map)

- [x] Merged `.incoming/il(2).json` + `.incoming/ps.json` into Israel polygon (outer + Gaza/WB holes) via `scripts/merge_israel_boundary.py`
- [x] Updated `dashboard/src/assets/countries.json` and `backend/src/data/countries.geojson`
- [x] Dashboard: cutout fill + interior stroke overlays in `MapViewer.jsx`; `boundaryUtils.js` + timeframe bounds fix
- [x] Review pass: sidebar return-live gated ≥1025px; origin halos use `getBoundaryOuter`; backend hole-aware ray-cast; simulator session reuse + config dotenv scope

## Signal Flare (scoped push)

Review fixes **shipped** (`0b9dd67`). Pass #2 follow-ups appended in [REVIEW-STATUS-SIGNAL-FLARE.md](REVIEW-STATUS-SIGNAL-FLARE.md#pass-2--post-ship-review-0b9dd67).

**Mobile wizard / push:** SW registers on boot (`registerSW` immediate); `skipWaiting` + `clients.claim`; push waits for `reg.active` not only `ready`. If SW still pending, prefs save and wizard closes with reload hint.

| Area | State |
|------|--------|
| Async web push | `asyncio.to_thread` in `push_manager.py` |
| Relay fanout | One broadcast per relay batch |
| API auth | `client_token` + `X-Push-Client-Token` |
| Wizard | `complete` after subscribe; `push_sw_pending` defers push and closes wizard |
| Tests | `pytest tests/test_alert_matching.py`, `npm run test` |

## Env required for push

- Backend: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL` (not default placeholder in prod), `MONGO_URI`
- Dashboard: `VITE_VAPID_PUBLIC_KEY`
- Generate: `npx web-push generate-vapid-keys`

## Backend venv

```bash
cd backend
.venv\Scripts\pip install -r requirements.txt
```

Includes `pywebpush==2.3.0` and `pytest`.

## Agent debug instrumentation (dashboard)

- [x] `agentDebugLog.js` — dev-only (`import.meta.env.DEV`), longtask throttle (2s), documented burst constants (`WS_MESSAGE_BURST`, `MAP_RESIZE_BURST`)
- [x] Sidebar — visualViewport resize only; `collapsedY` log outside state updater; removed spring/layout noise

## Mobile Chrome fixes (2026-05-23)

- [x] `MapViewer` — `ResizeObserver` + `visualViewport` sync + mount `invalidateSize` (half-tile map on viewport change)
- [x] `Sidebar` — snap collapsed sheet after first measure; `visualViewport` updates layout width/height
- [x] `vite.config.js` — `server.host: true` for phone testing on LAN

## SEO and Israeli compliance (dashboard v1.2)

- [x] `seoConfig.js` + `SEO.jsx` (react-helmet-async); English title/description; Hebrew in `keywords` meta only
- [x] Routes: `/`, `/about`, `/accessibility`, `/privacy`, `/terms`, 404
- [x] English legal pages; footer; cookie notice gating Vercel Analytics
- [x] High-contrast toolbar, skip link, `prefers-reduced-motion` (scroll-to-top removed — map shell does not scroll)
- [x] `og-image.png`, `favicon.png`, expanded `sitemap.xml`, `llms.txt`
- [x] Build prerender via `vite-prerender-plugin` for public routes
- [x] PWA manifest: English description, `lang: en`
- [x] `.cursor/rules/israeli-accessibility-is5568.mdc`, `review/is-5568-iron-sight.md`

### Search Console (manual — not done in repo)

Step-by-step checklist: [docs/GOOGLE_SEARCH_CONSOLE_SETUP.md](docs/GOOGLE_SEARCH_CONSOLE_SETUP.md)

1. [ ] Add property `https://iron-sight-drab.vercel.app` in [Google Search Console](https://search.google.com/search-console)
2. [ ] Verify (HTML file in `dashboard/public/` **or** meta tag in `index.html`)
3. [ ] Submit sitemap `https://iron-sight-drab.vercel.app/sitemap.xml`
4. [ ] Optional: URL inspection + request indexing for `/` and `/about`
5. [ ] Optional: Bing Webmaster Tools, Rich Results Test, OG debugger

Set `VITE_SITE_URL` in Vercel to `https://iron-sight-drab.vercel.app` and redeploy if changed.

## Dashboard audit fixes (2026-05-23)

- [x] Alert wizard auto-open restored (`shouldShowAlertWizard` + `openWizard` in `TacticalDashboard`)
- [x] Removed dead `AppShell.jsx`; splash `AnimatePresence` exit in `App.jsx`
- [x] Cookie notice: `aria-modal`, focus trap, Escape → Essential only; `essential` vs `accepted` consent
- [x] Alert wizard + cookie dialog: shared `useFocusTrap` (tab cycle + return focus)
- [x] `index.html` trimmed (Helmet owns SEO); `generate-sitemap.mjs` uses `VITE_SITE_URL`
- [x] Prerender unknown paths → noindex 404 stub; FAQ headings `h3` on About
- [x] `og-image.png` regenerated (~205 KB); removed unused prerender npm deps
- [x] Organization JSON-LD: product name Iron Sight + founder contact

## Handoff doc (tournament / other SPAs)

- [x] Full summary + replication steps: [docs/TOURNAMENT_HANDOFF_SEO_AND_UI.md](docs/TOURNAMENT_HANDOFF_SEO_AND_UI.md)

## Deploy

- [x] **MISSION**: Backend + dashboard production deploy (DEPLOY-2026-05-23) — [.milestone/backend_render_vercel_deploy.md](.milestone/backend_render_vercel_deploy.md)
- [x] **MISSION**: Dashboard push / SW boot deploy (DASH-PUSH-SW-01) — [.milestone/dashboard_push_sw_deploy.md](.milestone/dashboard_push_sw_deploy.md)

Post-deploy smoke (2026-05-23): health OK, VAPID public key matches Render/Vercel, `POST /api/history/update` → 401, dashboard map loads, `/api/history?hours=24` returns data.
