# Tactical alert simulator (development only)

Local relay mock for dashboard and engine testing. Not for production deployment.

## Requirements

- `IRON_SIGHT_DEV=1` or `ENV=development` in `backend/.env` (loaded automatically) or in the shell — process exits otherwise
- Listens on `127.0.0.1:8081` only (not reachable from LAN)
- `RELAY_AUTH_KEY` in environment — must match the key used by `main.py` when polling `/relay`
- Optional `SIMULATOR_DEV_TOKEN` — if set, POST `/dispatch` and `/end` require header `X-Simulator-Token`

## Wiring main.py

```env
IRON_SIGHT_DEV=1
RELAY_URL=http://127.0.0.1:8081/relay
RELAY_AUTH_KEY=<same secret as backend .env>
```

Start backend, then:

```powershell
$env:IRON_SIGHT_DEV = "1"
$env:RELAY_AUTH_KEY = "<your key>"
.\.venv\Scripts\python.exe simulator\server.py
```

## Credentials

Use a dev Mongo database and dev VAPID keys, or leave VAPID unset to disable push during sim.

Do not point sim relay at production `MONGO_URI` / VAPID: subscribed PWAs would receive Web Push for fake alerts before server-side filters; outbound policy now skips `is_simulation` for push and Telegram.

Simulation events still reach the dashboard over WebSocket; they are not persisted to salvo history, lifecycle logs, push, or Telegram.
