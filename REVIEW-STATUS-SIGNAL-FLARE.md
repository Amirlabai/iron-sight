# IRON SIGHT — Operation Signal Flare

**Codename:** `signal-flare`  
**Scope:** Scoped alert Web Push, onboarding wizard, server-side matching, service worker notifications.

**Goal:** Users receive background alerts only for their chosen perimeter (all / radius / exact), without blocking the tactical loop or leaking subscriptions.

**Last reviewed:** 2026-05-17 (pass #2 — commit `0b9dd67`)

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

---

## Pass #2 — post-ship review (`0b9dd67`)

**Verdict:** Beta-ready with VAPID/Mongo/HTTPS configured and modest subscriber count. Pass #1 items closed in commit; items below are follow-up only.

### Priority order (pass #2)

| # | ID | Severity | Status |
|---|-----|----------|--------|
| 13 | `push-subscribe-rate-limit` | 🟡 risk | `[ ]` |
| 14 | `push-fanout-scale` | 🟡 risk | `[ ]` |
| 15 | `push-geometry-test-drift` | 🟡 risk | `[ ]` |
| 16 | `push-point-harvest-drift` | 🟡 risk | `[ ]` |
| 17 | `push-subs-5000-cap` | 🟡 risk | `[ ]` |
| 18 | `push-token-localstorage` | 🟡 risk | `[-]` |
| 19 | `push-prune-lru` | 🔵 nit | `[ ]` |
| 20 | `push-unsubscribe-silent` | 🔵 nit | `[ ]` |
| 21 | `push-dedup-send-fail` | 🔵 nit | `[ ]` |
| 22 | `push-wizard-gps-fallback-copy` | 🔵 nit | `[ ]` |
| 23 | `push-delete-401-ambiguous` | 🔵 nit | `[-]` |
| 24 | `push-subscribe-token-model` | ❓ q | `[-]` |

### API & security (pass #2)

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-subscribe-rate-limit` | `[ ]` | `ws_manager.py:L70-79` | 🟡 `POST /subscribe` open; no rate limit — junk rows | Edge rate cap or throttle per IP |
| `push-token-localstorage` | `[-]` | `useAlertPreferences.js` | 🟡 `pushClientToken` in `localStorage` — XSS hijack | Accept PWA tradeoff; CSP/hardening |
| `push-subscribe-token-model` | `[-]` | `push_manager.py:L77` | ❓ Re-subscribe returns existing `client_token` with valid `endpoint`+`keys` | By design for reinstall; keys are secret |
| `push-delete-401-ambiguous` | `[-]` | `ws_manager.py:L119-121` | 🔵 DELETE 401 for bad token and missing row | OK for security; optional distinct codes in dev |

### Backend pipeline (pass #2)

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-fanout-scale` | `[ ]` | `push_manager.py:L147-171` | 🟡 O(events×subs) + `set_last_notified` per send each `multi_alert` | Queue/batch when subs grow |
| `push-subs-5000-cap` | `[ ]` | `mongo_manager.py:L347-348` | 🟡 `to_list(length=5000)` — subs above cap never notified | Paginate or cursor stream |
| `push-prune-lru` | `[ ]` | `push_manager.py:L39-41` | 🔵 Prune keeps last 50 by dict order, not LRU | Track timestamps or explicit eviction |
| `push-dedup-send-fail` | `[ ]` | `push_manager.py:L172-179` | 🔵 Failed send skips dedup persist — rare duplicate on retry | Touch dedup only after confirmed send (already mostly true; handle edge) |

### Matching & tests (pass #2)

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-geometry-test-drift` | `[ ]` | `alertMatching.test.js:L6-28` | 🟡 Vitest mocks `getEventTargetPoints`, not `mapGeometry.js` | Integration test against real `mapGeometry` or shared harvest helper |
| `push-point-harvest-drift` | `[ ]` | `alert_matching.py` vs `mapGeometry.js` | 🟡 Point harvesting duplicated; vectors test outcomes only | Shared harvest spec or cross-test hull/centroid cases |

### Dashboard (pass #2)

| ID | Status | Location | Problem | Fix |
|----|--------|----------|---------|-----|
| `push-unsubscribe-silent` | `[ ]` | `pushClient.js:L59` | 🔵 Server DELETE `.catch(() => {})` — local unsub OK, row may linger | Log/warn; retry DELETE |
| `push-wizard-gps-fallback-copy` | `[ ]` | `AlertPreferencesWizard.jsx:L58-59` | 🔵 Silent downgrade to `all` when GPS denied | UI copy explains fallback |

### Pass #2 smoke

- Subscribe → PATCH without `X-Push-Client-Token` → 401.
- Force 503 subscribe → wizard stays open (`complete: false`).
- Relay burst → event loop responsive (`to_thread` + semaphore).
- `pytest tests/test_alert_matching.py` + `npm run test` green.

### Pass #1 closed in `0b9dd67` (reference)

`asyncio.to_thread` + semaphore · `relay_batch_changed` · `client_token` auth · scope clamp · location `$set` guard · `complete` on sync fail · shared vectors + pytest/vitest · index on `endpoint` · `last_notified` prune.
