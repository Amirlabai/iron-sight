# MISSION: Backend + dashboard production deploy (DEPLOY-2026-05-23)

## Tactical scope and rationale

Ship the current `main` stack to production: Render hosts the Python tactical engine (`backend/`), Vercel hosts the dashboard (`dashboard/`). `status.md` lists deploy verification as open; local dashboard has uncommitted push/wizard fixes that must land before or with this deploy.

Goals:

- Render backend healthy with relay, MongoDB, VAPID, and CORS aligned to the live Vercel origin.
- Dashboard build on Vercel with correct API proxy, direct production WebSocket URL, and push keys.
- Post-deploy smoke: health, WS `multi_alert`, push subscribe, live relay ingest.

Out of scope: Google Search Console manual steps (see `docs/GOOGLE_SEARCH_CONSOLE_SETUP.md`), Kamatera relay infrastructure changes unless relay auth fails.

## Proposed technical changes

| Action | Path | Notes |
|--------|------|--------|
| MODIFY | Render service `iron-sight-backend` | Set env vars (see below); redeploy from `main`; confirm `render.yaml` `startCommand: python main.py` |
| MODIFY | `backend/.env.example` | Document `RELAY_URL`, `RELAY_AUTH_KEY`, `VAPID_*`, `VAPID_CLAIMS_EMAIL` (currently missing) |
| MODIFY | Vercel project (dashboard) | `VITE_SITE_URL`, `VITE_VAPID_PUBLIC_KEY`; confirm `vercel.json` rewrite target matches Render URL |
| MODIFY | `dashboard/` (local WIP) | Commit/push `pushClient.js`, `sw.js`, `AlertPreferencesWizard.jsx`, `useAlertPreferences.js`, `main.jsx`, `vite.config.js` before dashboard deploy |
| VERIFY | `version.json` | Backend logs version at boot; bump if releasing |
| NO CODE | Relay host | `RELAY_URL` + `x-relay-auth` must match Kamatera scout; no repo change unless URL rotated |

### Render environment (required)

```
MONGO_URI=<Atlas connection string>
DB_NAME=iron_sight_db
RELAY_URL=<Israel relay GET /alerts URL>
RELAY_AUTH_KEY=<relay secret>
ALLOWED_ORIGINS=https://iron-sight-drab.vercel.app,http://localhost:5173,http://localhost:5174
MISSION_KEY=<strong secret; must be set in prod>
VAPID_PUBLIC_KEY=<from npx web-push generate-vapid-keys>
VAPID_PRIVATE_KEY=<pair private key>
VAPID_CLAIMS_EMAIL=mailto:<real-ops-contact>
PORT=10000
```

Warnings from code:

- `VAPID_CLAIMS_EMAIL` default `mailto:ops@iron-sight.local` logs a startup warning (`src/main.py`).
- Unset `MISSION_KEY` leaves `/api/history/update`, split, merge, and calibrate unauthenticated (`ws_manager.py`).
- Unset `RELAY_URL` — engine sleeps only; no live ingest (`src/main.py`).

### Vercel environment (dashboard)

```
VITE_SITE_URL=https://iron-sight-drab.vercel.app
VITE_VAPID_PUBLIC_KEY=<same public key as Render>
```

Production WebSocket: dashboard must use `wss://iron-sight-hjwf.onrender.com/ws` directly (Vercel `/ws` rewrite does not upgrade). Confirm `dashboard/src/utils/constants.js` (or equivalent) matches deployed bundle.

Optional build speed: `PRERENDER=0` already in `vercel.json` build env.

### CORS

`ALLOWED_ORIGINS` must include the exact Vercel origin (no trailing slash). `aiohttp_cors` uses `allow_credentials=True`; avoid `*` in production.

## Verification plan

### Backend (local, before Render)

```powershell
Set-Location "c:\Users\amirl\OneDrive\Documents\GitHub\iron-sight\backend"
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: all tests pass (currently 118).

### Render (after deploy)

```powershell
curl -s https://iron-sight-hjwf.onrender.com/
```

Expected JSON: `status: OPERATIONAL`, `version` from `version.json`.

```powershell
curl -s https://iron-sight-hjwf.onrender.com/api/push/vapid-public-key
```

Expected: `publicKey` present when VAPID configured; else 503.

Tail Render logs for:

- `IRON SIGHT TACTICAL OPERATING SYSTEM` boot line
- No `VAPID_CLAIMS_EMAIL is default placeholder` in prod
- `RELAY_TIMEOUT` / `RELAY_CONNECTION_FAILURE` absent under normal relay load
- `DETECTION_SIGNAL` / `multi_alert` during live activity (or simulator)

### Dashboard (after Vercel deploy)

Manual:

1. Hard refresh; confirm splash clears and map loads (not stuck on old `index-*.js` hash).
2. DevTools Network: REST via `/api/...` → Render; WS to `wss://iron-sight-hjwf.onrender.com/ws` (not Vercel host).
3. Alert wizard: subscribe completes; no infinite "Saving…".
4. Receive test push (simulator or live alert) when scope matches.
5. `GET /api/history` via browser `/api/history?hours=24` returns data.

### Security smoke

```powershell
curl -s -o NUL -w "%{http_code}" -X POST https://iron-sight-hjwf.onrender.com/api/history/update -H "Content-Type: application/json" -d "{}"
```

Expected: `401` when `MISSION_KEY` is set.

## Rollback

- Render: redeploy previous successful deploy from dashboard.
- Vercel: promote previous deployment.
- Do not rotate VAPID keys unless invalidating all subscriptions is acceptable.

## Authorization gate

Do not run large code changes from this briefing without explicit go-ahead. Env-only Render/Vercel updates can proceed once secrets are confirmed.
