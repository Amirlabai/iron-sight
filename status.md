# Iron Sight — Status

**Updated:** 2026-05-17

## Signal Flare (scoped push)

Review fixes **shipped** (`0b9dd67`). Pass #2 follow-ups appended in [REVIEW-STATUS-SIGNAL-FLARE.md](REVIEW-STATUS-SIGNAL-FLARE.md#pass-2--post-ship-review-0b9dd67).

**Mobile wizard freeze:** save step could hang on `serviceWorker.ready` / push subscribe; dashboard now uses fetch/SW timeouts and always clears "Saving…".

| Area | State |
|------|--------|
| Async web push | `asyncio.to_thread` in `push_manager.py` |
| Relay fanout | One broadcast per relay batch |
| API auth | `client_token` + `X-Push-Client-Token` |
| Wizard | `complete` only after successful subscribe |
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

## Deploy

Verify Vercel dashboard build and Render backend after env keys are set.
