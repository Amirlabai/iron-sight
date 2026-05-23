# MISSION: Backend + dashboard production deploy (DEPLOY-2026-05-23)

## Tactical scope and rationale

Ship the current `main` stack to production: Render hosts the Python tactical engine (`backend/`), Vercel hosts the dashboard (`dashboard/`).

Goals:

- Render backend with relay ingest, MongoDB, VAPID, CORS, and `MISSION_KEY` aligned to the live Vercel origin.
- Dashboard build on Vercel with correct API proxy, direct production WebSocket URL, and push keys.
- Post-deploy smoke: env gates, auth, data reachability, log proof of ingest — not health JSON alone.

Out of scope: Google Search Console manual steps (see `docs/GOOGLE_SEARCH_CONSOLE_SETUP.md`), Kamatera relay infrastructure changes unless relay auth fails.

## Proposed technical changes

| Action | Path | Notes |
|--------|------|--------|
| MODIFY | Render service `iron-sight-backend` | Set env vars (see below); redeploy from `main`; confirm `render.yaml` `startCommand: python main.py` |
| MODIFY | `backend/.env.example` | Document `RELAY_URL`, `RELAY_AUTH_KEY`, `VAPID_*`, `VAPID_CLAIMS_EMAIL` (done in repo) |
| MODIFY | Vercel project (dashboard) | `VITE_SITE_URL`, `VITE_VAPID_PUBLIC_KEY`; confirm `vercel.json` rewrite target matches Render URL |
| VERIFY | `version.json` | Backend logs version at boot (`main.py` reads `version.json`); bump before release if marketing version matters |
| NO CODE | Relay host | `RELAY_URL` + `x-relay-auth` must match Kamatera scout; no repo change unless URL rotated |

**Note:** `render.yaml` declares only `PYTHON_VERSION` and `PORT`. All secrets are manual in the Render dashboard — git push alone does not set env. Confirm the checklist below before marking deploy complete.

### Render environment (required — deploy fails if any missing)

```
MONGO_URI=<Atlas connection string>
DB_NAME=iron_sight
RELAY_URL=http://63.250.61.251:3001/alerts
RELAY_AUTH_KEY=<relay secret; sent as x-relay-auth — do not leave unset>
ALLOWED_ORIGINS=https://iron-sight-drab.vercel.app,http://localhost:5173,http://localhost:5174
MISSION_KEY=<strong secret; required in prod>
VAPID_PUBLIC_KEY=<from npx web-push generate-vapid-keys>
VAPID_PRIVATE_KEY=<pair private key>
VAPID_CLAIMS_EMAIL=mailto:<real-ops-contact>
PORT=10000
```

Deploy blockers (code behavior):

| Condition | Code | Effect if violated |
|-----------|------|-------------------|
| `RELAY_URL` unset | `main.py` L125–126 | Sleep loop only; no ingest; `GET /` still OPERATIONAL |
| `RELAY_AUTH_KEY` unset | `main.py` L129 | Relay GET sends `x-relay-auth: None`; auth may fail |
| `MISSION_KEY` unset | `ws_manager.py` L176–178, L184, L243, L267 | History mutate routes unauthenticated |
| `ALLOWED_ORIGINS=*` | `config.py` L43–46 + `ws_manager.py` L22–27 | Wildcard with `allow_credentials=True` — avoid in prod |
| Default `VAPID_CLAIMS_EMAIL` | `main.py` L36–37 | Startup warning in logs |
| Either VAPID key missing | `push_manager.py` L50–58 | `GET /api/push/vapid-public-key` → 503 |

`DB_NAME` must match Atlas data. Live prod uses `iron_sight` (not code default `iron_sight_db`). Verify with non-empty history (see smoke below).

### Vercel environment (dashboard)

```
VITE_SITE_URL=https://iron-sight-drab.vercel.app
VITE_VAPID_PUBLIC_KEY=<same public key as Render>
```

Production WebSocket: dashboard uses `wss://iron-sight-hjwf.onrender.com/ws` directly (`constants.js` L65–75). Vercel `/ws` rewrite does not upgrade — verify WS host is Render, not Vercel.

Prod REST: `TACTICAL_API_URL=''` (`constants.js` L76) → push/history via Vercel `/api` rewrite. `ALLOWED_ORIGINS` mainly matters for direct Render calls and credentialed fetches.

`vercel.json` L9–10 hardcodes Render host; rotating Render service URL requires code + plan update together.

Optional build speed: `PRERENDER=0` already in `vercel.json` build env.

### CORS

`ALLOWED_ORIGINS` must be an explicit comma list including `https://iron-sight-drab.vercel.app` (no trailing slash). Do not use `*` in production.

## Verification plan

### Backend (local, before Render)

```powershell
Set-Location "c:\Users\amirl\OneDrive\Documents\GitHub\iron-sight\backend"
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: all tests pass (currently 118).

### Render env gate (manual dashboard — before sign-off)

Confirm every key in the Render table above is set. Treat missing `RELAY_URL`, `RELAY_AUTH_KEY`, or `MISSION_KEY` as deploy failure even if health curl passes.

### Render (after deploy)

**Reachability only (not sufficient alone):**

```powershell
curl.exe -s https://iron-sight-hjwf.onrender.com/
```

Expected JSON: `status: OPERATIONAL`, `version` from `version.json`. Relay/Mongo can be dead while this returns green — do not use as sole pass/fail.

**VAPID:**

```powershell
curl.exe -s https://iron-sight-hjwf.onrender.com/api/push/vapid-public-key
```

Expected: `publicKey` present (503 if either VAPID key missing).

**Mongo + DB_NAME:**

```powershell
curl.exe -s "https://iron-sight-hjwf.onrender.com/api/history?hours=24"
```

Expected: non-empty JSON array (proves `MONGO_URI` + `DB_NAME` match live data).

**Security smoke (`MISSION_KEY` must be set on Render):**

```powershell
# Missing auth header → 401 (not 400; 400 means auth passed and body validation failed)
curl.exe -s -o NUL -w "%{http_code}" -X POST https://iron-sight-hjwf.onrender.com/api/history/update -H "Content-Type: application/json" -d "{}"

# Invalid key → 401
curl.exe -s -o NUL -w "%{http_code}" -X POST https://iron-sight-hjwf.onrender.com/api/history/update -H "Content-Type: application/json" -H "X-Mission-Key: invalid" -d "{}"

# Valid key + empty body → 400 (missing required fields — proves auth layer passed)
curl.exe -s -o NUL -w "%{http_code}" -X POST https://iron-sight-hjwf.onrender.com/api/history/update -H "Content-Type: application/json" -H "X-Mission-Key: <MISSION_KEY>" -d "{}"

# Calibrate: same auth guard as history routes (ws_manager.py L174–178)
curl.exe -s -o NUL -w "%{http_code}" -X POST https://iron-sight-hjwf.onrender.com/api/calibrate
```

Expected: first two → `401`; third → `400`; calibrate without header → `401` when `MISSION_KEY` set. Calibrate is a no-op ping (returns `{"status":"SUCCESS"}`) but is **not** public when `MISSION_KEY` is set — same `if MISSION_KEY and header != MISSION_KEY` pattern. If calibrate returns 200 without header, `MISSION_KEY` is unset (deploy failure).

**Push subscribe (no `MISSION_KEY`; acceptable for launch):**

`POST /api/push/subscribe` has no mission auth (`ws_manager.py` L70–79). Anyone can register endpoints if VAPID + Mongo are up. Not in security smoke; abuse risk is low for launch.

**Log proof of live ingest (required — health/WS alone insufficient):**

Tail Render logs for:

- No `VAPID_CLAIMS_EMAIL is default placeholder`
- No sustained `RELAY_TIMEOUT` / `RELAY_CONNECTION_FAILURE`
- `DETECTION_SIGNAL` or `multi_alert` during live activity or simulator

Do not treat WS `health_status` OPERATIONAL as ingest proof — relay HTTP 200 with empty JSON still shows operational (`main.py` L280–286).

**Push delivery test:**

Push sends only when `events_list` non-empty (`main.py` L307–308). No push on full clear. Test push requires active or simulated alert matching subscription scope, not idle map.

**Post-deploy watch (not in original briefing):**

`push_manager.py` fanout is O(events × subs) per relay batch. Large subscription count during alert storms can stall the poll loop — watch Render CPU/latency.

### Dashboard (after Vercel deploy)

Manual:

1. Hard refresh; confirm splash clears and map loads (new `index-*.js` hash in Network tab).
2. DevTools Network: REST via `/api/...` → Render; WS to `wss://iron-sight-hjwf.onrender.com/ws` (not Vercel host).
3. Alert wizard: subscribe completes or closes cleanly with deferred push (no infinite "Saving…"). Requires `MONGO_URI` + both VAPID keys on Render.
4. Receive test push during simulator or live alert when scope matches.
5. `GET /api/history?hours=24` via browser returns data.

## Rollback

- Render: redeploy previous successful deploy from dashboard.
- Vercel: promote previous deployment.
- Do not rotate VAPID keys on routine redeploy — rotation invalidates all push subscriptions.

## Known live-ingest caveats (not deploy env, but affects post-deploy live test)

- `main.py` L180–186: generic clearance without `alert_id` ends all active events — bad relay end payload can false "all clear".
- `main.py` L280–286: WS health OPERATIONAL when relay HTTP 200 even if JSON empty.

## Authorization gate

Do not run large code changes from this briefing without explicit go-ahead. Env-only Render/Vercel updates can proceed once secrets are confirmed.

---

## Implementation Record

Completed: 2026-05-23

### Changes Deployed

| File | Change |
|---|---|
| `backend/.env.example` | Document relay, VAPID, `DB_NAME=iron_sight` |
| `dashboard/.env.example` | Add `VITE_VAPID_PUBLIC_KEY` |
| `dashboard/src/main.jsx` | Immediate `registerSW` on boot |
| `dashboard/src/sw.js` | `skipWaiting` + `clients.claim` |
| `dashboard/src/utils/pushClient.js` | `ensureServiceWorkerRegistration`, 20s timeout |
| `dashboard/src/hooks/useAlertPreferences.js` | `push_sw_pending` deferred path |
| `dashboard/vite.config.js` | `injectRegister: null` |
| `dashboard/src/utils/pushClient.test.js` | SW registration mocks |
| `status.md` / `context.md` | Deploy smoke notes and mission close-out |

### Summary

Shipped dashboard push/SW fixes via `a2ecbe9` (v0.23.0). Render env verified live: VAPID, `MISSION_KEY` (401 on unauth mutate), Mongo history non-empty, relay ingest operational. Briefing updated with deploy blockers, corrected auth smoke (401 vs 400), and log-based ingest proof — health JSON alone is insufficient.

