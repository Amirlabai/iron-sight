# Iron Sight — Status

**Updated:** 2026-06-08

## Current state

Production live: Render backend + Vercel dashboard (`iron-sight-drab.vercel.app`). Relay ingest operational. Alpha development.

## Recently completed

### Backend observability (worktree `.worktrees/observability`, branch `fix/observability-logs`)

- `observability.py`: RSS memory, HTTP timing middleware, structured log helpers.
- `main.py`: `RUNTIME`, `RELAY_POLL` heartbeat (~60s), `BROADCAST` cache hit/miss + bytes, `LIFECYCLE_PURGE` summary.
- `ws_manager.py`: `HISTORY_FETCH` rows/bytes/duration, `WS_CONNECT`/`WS_DISCONNECT`, HTTP middleware for `/api/*`.
- `LOG_LEVEL` and `POLL_HEARTBEAT_EVERY` env vars.
- Slim history API: `view=list` (default) for pagination; `GET /api/history/event` for full archive on select; WS `history_sync` uses slim rows.

### History pagination fix (2026-06-08)

- `mongo_manager.py`: `get_consolidated_history_page` / `get_history_page` with limit+1 `has_more`; consolidated queries exclude `newsFlash`.
- `GET /api/history?page=1` returns `{ items, has_more, next_offset }`; legacy array response unchanged without `page=1`.
- Dashboard: consumes page envelope; WS `history_sync` sets `historyHasMore` from server `has_more`.
- Fixes sidebar SHOW MORE hidden when API had newsFlash rows or WS sync cleared pagination state.

### History memory trim (2026-06-08)

- Dashboard always uses `view=list` for sidebar/timeframe fetches (was `view=full` for time filters → 17MB responses, RSS ~380MB).
- Slim list rows keep cluster centroids + trajectory origin pins for timeframe merge; full geometry only on card select.
- `selectArchive` dedupes in-flight detail fetches and caches by id; abort stale history list requests on filter change.
- Backend: 1000-row time-window cap applies only to `view=full` (operator tools).

### Progressive archive loading (2026-06-08)

- All Time: first fetch last 24h, 10 slim rows per page; SHOW MORE pages within window then extends +24h (up to 90d).
- Empty windows auto-advance until rows found or cap; fixed filters (1H/12H/24H/range) unchanged.

### Timeframe full fetch + map render budget (2026-06-08)

- Timeframe filters (1H/12H/24H/range): fetch all slim rows in window (100/page, cap 5000); no SHOW MORE.
- `mapRenderBudget.js`: timeframe = hulls only; multi-event suppress city dots/bounds at 80+ cities or 500+ total.

### EventStore review refactor (branch `refactor/event-store-review`, worktree `.worktrees/refactor-review`)

- `missile_origins.py`: shared `build_missile_origins` — live, merge, and archive paths use one pipeline.
- `lifecycle.py` / `relay_ingest.py`: `main.py` slimmed to poll loop + `maintain_lifecycle` + `ingest_relay_batch`.
- `event_store.py`: union-city clustering view for master assignment; `_rebuild_master` returns total; timeout sync via `_cluster_stub_ids`; full invalidate on stub mutations.
- `threat_processor.py`: `_process_per_city_markers`; missiles path uses centroid only (no discarded hull).
- `cluster_utils.py`: `QhullError` instead of bare except; removed `get_cluster_groups` alias.
- `mongo_manager.py`: single `_updated_lifecycle_op` for debounced vs full UPDATED writes.
- Tests: merge-cache invalidation on real `set_field`; 220 passed.

### OOM memory refactor (2026-06-08)

- `event_store.py`: stub+master in-memory model — one canonical analysis payload per cluster, per-relay city subsets on stubs.
- `main.py`: skip no-op relay updates (+0 cities); merge broadcast cache; `CLUSTER_TIMEOUT_SYNC` only on real city deltas.
- `threat_processor.py` / `cluster_utils.py`: coord-only hulls in live RAM; polygon hulls at broadcast/persist only.
- `mongo_manager.py`: debounce `UPDATED` lifecycle writes when city count unchanged within 30s.
- Tests: `test_event_store.py`, `test_log_event_dedup.py`.

### PWA WebSocket reconnect (2026-06-08)

- `wsReconnect.js`: first 3 reconnect waits stay at 3s each, then 6s → 12s → … (cap 60s).

### Calc/display split + review fixes (2026-06-08)

- `project_calc_entry` for calc-border APIs; `get_projected_origin` is display-only alias.
- `entry_by_origin` / history-fixer suggest-origin use calc entry; live trajectories store tactical display pin.
- `recalc_regional_trajectories.py`: non-dry-run writes require `--all`; optional `--origins` filter.
- Dashboard: origin filter auto-load cap 4 pages; stay on archive tab when filter clears selection.

### Archive normalize + dashboard verified display (2026-06-08)

- `archive_normalize.py`: `normalize_missile_archive` rebuilds unverified legacy rows (collapse multi-trajectory, unified cluster hull, tactical display pins); `dedupe_verified_missile_archive` for verified/manual rows (`--dedupe-verified`).
- `recalc_regional_trajectories.py`: uses normalize helpers; skips committed rows by default.
- `ws_manager.py`: verify commit stores single trajectory only.
- Dashboard: `trajectoriesForDisplay` in archive map — verified/manual rows render `trajectories[0]` only.
- Tests: `test_archive_normalize.py`, updated `test_recalc_regional_trajectories.py`.

### Tactical display pin (2026-06-08)

- `engine.py`: calc-border detection unchanged; display pin = first tactical silhouette crossing + 0.1° inset along full ray to `tac_max` (not deepest hit, not calc entry). Fixes Iraq/Iran gap (North Iran calc quad vs tactical silhouette). On-ray `tac_max` fallback before country-centroid. `calc_entry_coords` on trajectories; origin replay shows calc vs display markers.
- Dashboard: shared `buildOriginMarkerIcon`; origin marker anchored at pin center (trajectory line meets pin, not label gap).
- Tests: `test_origin_detection.py`, `test_ray_march.py` (display pin + fallback).

### Vectorized calc-border ray march (2026-06-08)

- `engine.py`: 0.1° ray grid + numpy batch point-in-polygon; `entry_inset` applies to all origins; removed binary-search march.

### Origin Replay dev tool (2026-06-02)

- Backend: `origin_replay.py` + `POST /api/origin/replay` (mission-key gated); engine helpers extracted for vector/projection trace.
- Live trajectories: `origin_coords` / `marker_coords` = tactical display pin via `project_origin_display`; calc entry in optional `calc_entry_coords`.
- History-fixer: `entry_by_origin` / `project-entry` use `project_calc_entry` (calc-border); verify commit stores operator pin.
- API: `POST /api/history/suggest-origin` returns `entry_by_origin`; `POST /api/history/project-entry` for label-only relabel.
- Archive recalc: `backend/scripts/recalc_regional_trajectories.py` — full normalize for unverified missiles; `--dedupe-verified` for history-fixer rows. See `src/utils/archive_normalize.py`.
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
