#include <.context/COMMUNICATION_PROTOCOL.md>
#include <.context/UI_DESIGN_SPEC.md>
#include <.context/MOBILE_SHELL_SPEC.md>

# Iron Sight — Context

Before changing communication (headers, endpoints, payloads), read [SCP](.context/COMMUNICATION_PROTOCOL.md). Before UI/theme/component work, read [UI Design Spec](.context/UI_DESIGN_SPEC.md). Before mobile shell, boot, or PWA changes, read [Mobile Shell Spec](.context/MOBILE_SHELL_SPEC.md). Track UX audits in [REVIEW-STATUS.md](REVIEW-STATUS.md).

## Purpose

Real-time tactical intelligence for the Israeli theater. Ingests Pikud HaOref alerts, clusters and vectorizes threats, and renders them on a strategic map dashboard.

## Core logic (TACTICAL-CORE-v1.2)

- Regional adjacency merge: same-region on 1 shared city; cross-region needs 50% city intersection.
- One trajectory per origin group (Lebanon, Gaza, etc.).
- Origin = country label (`trajectory.origin`) plus display pin on the tactical country silhouette. `origin_coords` and `marker_coords` are always the same (pin, line start, stored geometry). Classification and replay calc step use **calc** borders (`calculation_borders.json`); display pin ray-marches into **tactical** polygons (`countries.geojson`) with country-centroid fallback when the ray misses the silhouette.

| API / field | Coords |
|-------------|--------|
| `entry_by_origin`, `project-entry`, `project_calc_entry` | Calc-border entry |
| Live `origin_coords` / `marker_coords` | Tactical display pin |
| `calc_entry_coords` (optional on trajectory) | Calc-border entry for replay/debug |
| History-fixer verify commit | Operator-chosen pin (typically calc entry from suggest-origin) |

- Origin projection via regression from cluster cities; depth calibration: Gaza/Lebanon 0.5, Iran 16.0, Yemen 20.0. Trajectory entry: calc-border ray-march along oriented PCA, then ~0.1° inset inside calc polygon. Display pin: first **tactical silhouette** crossing on the full ray (to `tac_max` 42° Iran / 50° Yemen) plus 0.1° inset—never calc entry coords. Fallback: on-ray point at `tac_max` if inside silhouette, else country-centroid. Optional `calc_entry_coords` on trajectory for replay/debug.
- ID-driven lifecycle: `EventStore` (stub per relay ID + one master analysis per cluster); 10s end grace; 20 min inactivity timeout. Duplicate relay ticks (+0 cities) skip reprocess, broadcast, DB `UPDATED`, and cluster timeout extension.
- Live RAM uses coord-based hulls; polygon hulls built only for WebSocket broadcast and DB persist.
- Strategic origins (Iran/Yemen) gated by warning-shaped `newsFlash` (`data` or `cities` present).
- When **≥2** geometric origin candidates exist, `origin_ml.resolve_origin_ml` picks the winner from **verified** `salvo_history` / `drone_history` (labels: `verified`, `manual_origin`, `trajectories[0].origin`).
- newsFlash persisted to `newsflash_history` with `lifecycle_status` (`ended` / `superseded` / `cleared`); excluded from origin ML.
- newsFlash ghosts superseded by overlapping confirmed missile alerts.

## Architecture

| Layer | Stack | Notes |
|-------|-------|-------|
| Backend | Python 3.12, `backend/src/` | Core engine, REST/WS API, MongoDB persistence |
| Dashboard | Vite + React, `dashboard/` | Leaflet map, glassmorphic UI, PWA |
| Origin Replay | Vite + React, `origin-replay/` | Dev tool: step-through origin pipeline replay (`:5175`) |
| Database | MongoDB Atlas (M0) | Threat archives + `event_logs` lifecycle |
| Deploy | Render (API) / Vercel (UI) / Kamatera (relay) | Prod WS: `wss://iron-sight-hjwf.onrender.com/ws`; REST via Vercel `/api` rewrite |
| Relay | Node.js scout (`63.250.61.251`) | GET `/alerts` + `x-relay-auth`; sole uplink |

### Backend modules

- `src/core/` — clustering, PCA vectoring, multi-threat processing (missiles, drones, infiltration, earthquake, newsFlash); `origin_replay.py` for dev step-through trace.
- `src/api/` — WebSocket sync, REST history/cities, push routes; `POST /api/origin/replay` for origin pipeline replay.
- `src/utils/` — trajectory helpers, `archive_normalize.py` (legacy missile archive rebuild).
- Geodata — `tactical_borders.json` (visuals), `calculation_borders.json` (logic), `cities.json` / `polygons.json` (city boundaries).

### Dashboard highlights

- Routes: `/`, `/about`, `/accessibility`, `/privacy`, `/terms` (legal pages prerendered; `/` is client-only).
- SEO: `seoConfig.js`, `SEO.jsx`, `VITE_SITE_URL`, build-time sitemap; cookie banner on map route.
- Map: Leaflet, origin corridors, country silhouettes (`countries.json`), city boundary strokes, `TacticalMotionLayer` (missiles + interceptors), `TrackingDrone` (drones), `UserLocationMarker` (blue dot when geo granted). Motion sprites: inbound `rocket.png`, interceptors `anti-missile.png`, drones `drone.png`; PNG top = forward for rotatable units; `screenBearingBetween` + `motionSpriteTransformCss`; center via Leaflet `iconAnchor` + wrap flex; optional `SPRITE_HEADING_OFFSET_DEG` in `trajectoryPaths.js`.
- Mobile shell: fixed bottom sheet, motion-value drag, 45px header — see Mobile Shell Spec.
- Alert prefs: scoped push (all/radius/exact), partitioned localStorage/sessionStorage, optional Telegram Kfar Kama alerts.
- Simulation (`is_simulation`): dashboard WebSocket only; no Web Push, Telegram, salvo persist, or `event_logs` lifecycle writes. Local relay: `backend/simulator/` on `127.0.0.1:8081` with `IRON_SIGHT_DEV=1` and matching `RELAY_AUTH_KEY`.

## Frontend module map

| Path | Role |
|------|------|
| `context/TacticalProvider.jsx` | Global state, WS lifecycle, audio |
| `utils/constants.js` | Env, WS URLs, colors, geodata |
| `components/Map/MapViewer.jsx` | Leaflet container |
| `components/Map/ThreatOverlay.jsx` | Clusters, trajectories, boundaries |
| `components/Map/TacticalMotionLayer.jsx` | Missile intercept animation |
| `components/Map/TrackingDrone.jsx` | Drone waypoint patrol |
| `components/Sidebar/Sidebar.jsx` | Live/History/Sandbox drawer |
| `styles/layout.css` | Shell geometry (≥1025px desktop, ≤1024px mobile) |
| `App.css` | Component visuals |
| `styles/animations.css` | Keyframes |

## Key docs

- Deploy: [.milestone/backend_render_vercel_deploy.md](.milestone/backend_render_vercel_deploy.md)
- Push/SW: [.milestone/dashboard_push_sw_deploy.md](.milestone/dashboard_push_sw_deploy.md)
- Signal Flare review: [REVIEW-STATUS-SIGNAL-FLARE.md](REVIEW-STATUS-SIGNAL-FLARE.md)
- SEO handoff: [docs/TOURNAMENT_HANDOFF_SEO_AND_UI.md](docs/TOURNAMENT_HANDOFF_SEO_AND_UI.md)
- Search Console setup: [docs/GOOGLE_SEARCH_CONSOLE_SETUP.md](docs/GOOGLE_SEARCH_CONSOLE_SETUP.md)
