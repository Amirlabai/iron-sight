# Iron Sight — Status

**Updated:** 2026-06-01

## Current state

Production live: Render backend + Vercel dashboard (`iron-sight-drab.vercel.app`). Relay ingest operational. Alpha development.

## Recently completed

### Map motion visuals (2026-06-01)

- Inbound missile and drone: CSS chevrons (unchanged). Interceptor: `sprites/rocket.png` at 20px. Drop upright rocket into `public/sprites/` and set `INTERCEPTOR_ART_HEADING_CCW` to 90 in `TacticalMotionLayer.jsx`.

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
