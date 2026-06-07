# Iron Sight — Status

**Updated:** 2026-06-08

## Current state

Production live: Render backend + Vercel dashboard (`iron-sight-drab.vercel.app`). Relay ingest operational. Alpha development.

## Recently completed

### PWA WebSocket reconnect (2026-06-08)

- `wsReconnect.js`: first 3 reconnect waits stay at 3s each, then 6s → 12s → … (cap 60s).

### Origin Replay dev tool (2026-06-02)

- Backend: `origin_replay.py` + `POST /api/origin/replay` (mission-key gated); engine helpers extracted for vector/projection trace.
- Unified origin coords: one border-entry point for pin + line + storage; live writes sync `origin_coords` and `marker_coords`; dashboard/history-fixer read `origin_coords` first.
- Trajectory entry: `get_projected_origin` ray-marches calc borders on oriented regression ray (no country-center pin).
- API: `POST /api/history/suggest-origin` returns `entry_by_origin`; `POST /api/history/project-entry` for label-only relabel.
- Archive recalc: `backend/scripts/recalc_regional_trajectories.py` (Gaza/Lebanon; syncs both coord fields).
- Standalone app: `origin-replay/` on `:5175` — archive picker, step navigator, Leaflet overlays per pipeline stage.
- Tests: `backend/tests/test_origin_replay.py`, `test_trajectory_utils.py`.

### Simulation outbound isolation (2026-06-01)

- Push and Telegram skip `is_simulation` via `outbound_policy.skip_outbound_event`; `_broadcast_multi_alert` filters push list.
- `main.py`: no lifecycle `log_event` for sim; health `upstream_source` is `SIMULATOR` for local relay or sim batches.
- Simulator: dev guard (`IRON_SIGHT_DEV` / `ENV=development`), bind `127.0.0.1`, `x-relay-auth` on `/relay`, localhost-only dispatch/UI.
- Docs: `backend/.env.example`, `backend/simulator/README.md`.

### Map motion sprites (2026-06-01)

- Sprites: `rocket.png`, `drone.png`, `anti-missile.png` (32px); interceptors at 20px. Splash: classic CSS radar sweep. Source: `sprites/sprite files/*.newt` → `node scripts/newt-to-png.mjs`.
- Centering: Leaflet `iconAnchor` + inline negative margins (do not zero margin on div icons); `.motion-sprite-wrap` flex; JS `rotate()` only on sprites.

## Previously completed

### Origin ML + history training (2026-06-01)

- Multi-origin disambiguation (`origin_ml.py`): when ≥2 candidates, score verified archive and collapse to one salvo card.
- Live merge: missile IDs with shared cities merge despite origin mismatch; ML runs on union.
- newsFlash archive: `newsflash_history` + `lifecycle_status` on lifecycle purge.
- history-fixer: ML scores panel, training queue filters, export verified JSON, `manual_origin` on verify.
- API: `POST /api/history/suggest-origin`, `GET /api/history/training-export`.
- Ops: removed false Iran salvo `134247350860000000` (טבריה / מצפה / כפר חיטים).
- Tests: 158 passed (`backend\.venv\Scripts\python.exe -m pytest tests/`).

### Tactical motion (2026-05-30)

- Missiles: `TacticalMotionLayer` intercept loop (arc-length speed).
- Drones: `TrackingDrone.jsx` restored (city-to-city legs); removed from unified motion layer.
- Fixes: single-city drone stutter, missile burst remount on live planKey update.
- Tests: 151 passed (`backend\.venv\Scripts\python.exe -m pytest tests/`).

### Telegram Kfar Kama (2026-05-30)

- ACTIVE (map PNG) / ENDED (text) via `telegram_notifier.py`; skips simulation.
- Dedup, lock serialization, stale-id revalidation, newsFlash supersede END hook.
- Env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `KFAR_KAMA_ALERT_LAT`/`LNG`.

### Dashboard (2026-05-28)

- Theme: persisted light/dark, map tile switch, legal-page tokens.
- City boundaries: backend `city_id`/`boundary` in payloads; per-city strokes on map; live label cap.
- History: `/api/history` pagination (`limit`/`offset`), archive SHOW MORE, backfill script.
- Alert prefs: partitioned storage, debounced persist, LRU dedupe caps.
- Timeframe merge: 8 km centroid proximity; merged hull from city coords only.

### Infrastructure (shipped)

- Prod WS direct to Render; Vercel `/api` rewrite for REST; `PRERENDER=0` for fast CI builds.
- Push/SW boot: immediate register, `skipWaiting`, deferred `push_sw_pending`.
- Israel boundary cutout (Gaza/WB holes); mobile shell contract; SEO/compliance v1.2.
- Signal Flare scoped push shipped; review log in [REVIEW-STATUS-SIGNAL-FLARE.md](REVIEW-STATUS-SIGNAL-FLARE.md).

## Open / manual

- [ ] Google Search Console — see [docs/GOOGLE_SEARCH_CONSOLE_SETUP.md](docs/GOOGLE_SEARCH_CONSOLE_SETUP.md)
- [ ] Socket sync audit — [.open_work/socket_sync_review.md](.open_work/socket_sync_review.md)
- [ ] Relay auth migration to server-side secrets — [.open_work/frontend_modularization.md](.open_work/frontend_modularization.md)

## Env quick ref

**Push:** `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL`, `VITE_VAPID_PUBLIC_KEY` — generate via `npx web-push generate-vapid-keys`

**Backend venv:**

```powershell
cd backend
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/
```

**Fast dashboard build:** `$env:PRERENDER='0'; npm run build` (~10s)
