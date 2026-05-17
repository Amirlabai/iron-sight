# IRON SIGHT — Operation Signal Flare

**Codename:** `signal-flare`  
**Scope:** Scoped alert Web Push, onboarding wizard, server-side matching, service worker notifications.

**Goal:** Users receive background alerts only for their chosen perimeter (all / radius / exact), without blocking the tactical loop or leaking subscriptions.

**Last reviewed:** 2026-05-17 (review fixes shipped)

**Sibling audit:** [REVIEW-STATUS.md](REVIEW-STATUS.md) — Smooth UX / shell / performance (separate track).

**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` wontfix / deferred

---

## Priority order

| # | ID | Severity | Status |
|---|-----|----------|--------|
| 1 | `push-sync-webpush` | 🔴 bug | `[x]` |
| 2 | `push-complete-on-fail` | 🔴 bug | `[x]` |
| 3 | `push-api-auth` | 🔴 bug | `[x]` |
| 4 | `push-relay-fanout` | 🟡 risk | `[x]` |
| 5 | `push-location-404` | 🟡 risk | `[x]` |
| 6 | `push-scope-validate` | 🟡 risk | `[x]` |
| 7 | `push-resubscribe-location` | 🟡 risk | `[x]` |
| 8 | `push-matching-drift` | 🟡 risk | `[x]` |
| 9 | `push-endpoint-index` | 🟡 risk | `[x]` |
| 10 | `push-last-notified-growth` | 🔵 nit | `[x]` |
| 11 | `push-notify-key-semantics` | ❓ q | `[x]` |
| 12 | `push-vapid-email-default` | 🔵 nit | `[x]` |

---

## API & security

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-api-auth` | `[x]` | `ws_manager.py` push handlers | 🔴 No auth; known `endpoint` → PATCH location / DELETE | `client_token` on subscribe; `X-Push-Client-Token` on PATCH/DELETE |
| `push-location-404` | `[x]` | `ws_manager.py`, `mongo_manager` | 🟡 200 when endpoint unknown | 404 when `matched_count == 0` |
| `push-scope-validate` | `[x]` | `push_manager.py` | 🟡 Arbitrary scope/radius | Whitelist + clamp 3–30 km |

---

## Backend pipeline

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-sync-webpush` | `[x]` | `push_manager.py` | 🔴 Sync `webpush()` blocks loop | `asyncio.to_thread` + semaphore |
| `push-relay-fanout` | `[x]` | `main.py` | 🟡 Push every alert in batch loop | Single `_broadcast_multi_alert` per relay batch |
| `push-endpoint-index` | `[x]` | `mongo_manager` | 🟡 No unique index | `create_index("endpoint", unique=True)` |
| `push-resubscribe-location` | `[x]` | `mongo_manager` | 🟡 Resubscribe clears coords | `$set` location only when provided |
| `push-last-notified-growth` | `[x]` | `push_manager` | 🔵 Map grows unbounded | Prune to active alert ids, cap 50 |
| `push-notify-key-semantics` | `[x]` | `alert_matching.py` / `.js` | ❓ `id:cityCount` dedup | Documented: re-push when city count grows |

---

## Matching duplication

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-matching-drift` | `[x]` | `shared/alert_matching_vectors.json` | 🟡 Duplicated logic | Shared vectors + pytest + vitest |

---

## Dashboard & client

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-complete-on-fail` | `[x]` | `useAlertPreferences.js`, wizard | 🔴 `complete: true` on fail | `complete` only when sync ok; error on confirm |
| `push-patch-silent-fail` | `[x]` | `pushClient.js` | 🟡 Silent PATCH fail | Auth header + dev warn + retry on 5xx |
| `push-wizard-scope-fallback` | `[-]` | `AlertPreferencesWizard.jsx` | 🔵 GPS denied → all | Documented UX |

---

## Ops & config

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-vapid-email-default` | `[x]` | `config.py`, `main.py` | 🔵 Placeholder email | Startup warning if default |
| `push-requirements-newline` | `[x]` | `requirements.txt` | 🔵 Missing EOF newline | Fixed |

---

## Shipped (implementation baseline)

| ID | Status | Location | Notes |
|----|--------|----------|-------|
| `signal-flare-wizard` | `[x]` | `AlertPreferencesWizard.jsx` | Post-boot notify + GPS + scope flow |
| `signal-flare-vapid-routes` | `[x]` | `ws_manager.py` `/api/push/*` | Subscribe, location, unsubscribe, VAPID key |
| `signal-flare-server-match` | `[x]` | `push_manager.py`, `alert_matching.py` | Server-side scope filter + dedup |
| `signal-flare-sw` | `[x]` | `sw.js` | Push display + notification click focus |
| `signal-flare-client-audio` | `[x]` | `TacticalProvider.jsx` | In-tab audio filtered by scope |
| `signal-flare-expired-sub` | `[x]` | `push_manager.py` | 404/410 removes dead subscriptions |

---

## Verify on device

HTTPS subscribe → background push (app closed) → radius vs exact vs all with simulator/relay; re-open wizard after forced subscribe failure; PATCH without token → 401.

---

## Notes

- Feature env: `VAPID_*`, `MONGO_URI`, `VITE_VAPID_PUBLIC_KEY` — see [status.md](status.md).
- Tests: `backend` → `pytest tests/test_alert_matching.py`; `dashboard` → `npm run test`.
- Do not mix Signal Flare items into [REVIEW-STATUS.md](REVIEW-STATUS.md); cross-link only.
