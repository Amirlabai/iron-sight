# MISSION: dashboard-push-sw-boot (DASH-PUSH-SW-01)

## Tactical scope and rationale

Staged dashboard changes fix mobile alert-wizard hangs and missed background push when the service worker was not active at save time. Root cause: push flow waited on `navigator.serviceWorker.ready` while Vite PWA registration was deferred (`injectRegister: 'script-defer'`), so first-save could block or fail on cold load and installed PWA.

Goals after deploy:

- SW registers at app boot (`registerSW({ immediate: true })`).
- Push subscribe waits for `reg.active` via `ensureServiceWorkerRegistration` / `waitForWorkerActive`.
- SW updates take control quickly (`skipWaiting`, `clients.claim`).
- Wizard does not freeze on SW timeout; prefs persist with deferred push when SW is still installing.

Out of scope for this mission: backend VAPID/Mongo changes, Search Console, prerender route changes.

## Proposed technical changes

| Action | File | Summary |
|--------|------|---------|
| MODIFY | `dashboard/vite.config.js` | `injectRegister: null` — drop auto-injected defer script; registration owned by app |
| MODIFY | `dashboard/src/main.jsx` | `registerSW({ immediate: true })` before React mount |
| MODIFY | `dashboard/src/sw.js` | `install` → `skipWaiting`; `activate` → `clients.claim()` |
| MODIFY | `dashboard/src/utils/pushClient.js` | `ensureServiceWorkerRegistration`, `waitForWorkerActive`, `SW_READY_MS` 20s, fallback `register('/sw.js')` |
| MODIFY | `dashboard/src/hooks/useAlertPreferences.js` | `push_sw_pending` path: mark prefs complete, close wizard, return `pushDeferred` |
| MODIFY | `dashboard/src/utils/pushClient.test.js` | Mocks updated for `getRegistration` path |
| MODIFY | `status.md` | Signal Flare note aligned with SW boot behavior |

### Follow-ups (not in staged diff — consider before or right after deploy)

| Action | File | Summary |
|--------|------|---------|
| MODIFY | `dashboard/src/components/Onboarding/AlertPreferencesWizard.jsx` | User-visible copy when `pushDeferred` / reload needed (status.md claims reload hint; wizard UI does not yet) |
| NEW (optional) | `dashboard/src/hooks/useAlertPreferences.js` or `App.jsx` | On boot: if `notifyPermission === 'granted'` && `!pushEndpoint`, call `registerPush()` once SW is ready |
| MODIFY | `status.md` | Table row "Wizard \| complete only after successful subscribe" conflicts with `push_sw_pending` → `complete: true` |

## Deploy targets

| Surface | Host | Notes |
|---------|------|-------|
| Dashboard | Vercel (`iron-sight-drab.vercel.app`) | Root `dashboard/` or monorepo dashboard project; `PRERENDER=0` in `vercel.json` |
| Backend push API | Render (`iron-sight-hjwf.onrender.com`) | No code change required if VAPID env already set |

## Environment checklist (Vercel dashboard project)

- `VITE_VAPID_PUBLIC_KEY` — must match backend `VAPID_PUBLIC_KEY`
- `VITE_SITE_URL` — `https://iron-sight-drab.vercel.app` (canonical / sitemap)
- Optional: keep `PRERENDER=0` for fast builds (already in `dashboard/vercel.json`)

## Verification plan

### Local (pre-push)

```powershell
Set-Location "c:\Users\amirl\OneDrive\Documents\GitHub\iron-sight\dashboard"
npm run test
npm run build
```

### Manual — desktop Chrome

1. Hard refresh (empty cache) on dev or preview URL.
2. DevTools → Application → Service Workers: `/sw.js` registered, status activated.
3. Complete alert wizard with notifications allowed; confirm no infinite "Saving…".
4. Application → Push: subscription present; Network: `POST /api/push/subscribe` 200 with `client_token`.

### Manual — mobile Chrome (LAN or production)

1. Open site (prefer installed PWA after first visit).
2. Run wizard; if SW slow, confirm wizard closes (not stuck) and prefs saved in localStorage (`iron_sight_alert_prefs`).
3. Reload once; confirm push subscription appears and test notification from backend or devtools push (if available).

### Post-deploy production

1. Confirm new asset hash in Network tab (not stale `index-*.js`).
2. `https://iron-sight-drab.vercel.app/sw.js` returns 200, `Cache-Control: no-cache`.
3. Spot-check: map loads (no black screen), WS connects to Render `wss://…/ws`, wizard + push on phone.

### Rollback

- Revert commit on `main` and redeploy Vercel, or promote previous deployment in Vercel dashboard.
- Users with stuck SW: clear site data or wait for `autoUpdate` cycle after rollback build.

## Authorization

Implementation is staged locally. Await explicit user go-ahead to commit, push, and trigger Vercel production deploy.

---

## Implementation Record

Completed: 2026-05-23

### Changes Deployed

| File | Change |
|---|---|
| `dashboard/vite.config.js` | `injectRegister: null` |
| `dashboard/src/main.jsx` | `registerSW({ immediate: true })` |
| `dashboard/src/sw.js` | `skipWaiting` + `clients.claim` |
| `dashboard/src/utils/pushClient.js` | `ensureServiceWorkerRegistration`, 20s timeout |
| `dashboard/src/hooks/useAlertPreferences.js` | `push_sw_pending` deferred path |
| `dashboard/src/utils/pushClient.test.js` | SW registration mocks |
| `status.md` | Wizard row + Signal Flare note aligned |

### Summary

Shipped via `a2ecbe9` to Vercel prod. Cold-load wizard no longer hangs on deferred SW; push waits for `reg.active`. Deferred follow-ups: wizard reload copy, optional boot push retry.
