# History Fixer — training console

Operator tool for verifying salvo origins and building the ML training corpus in MongoDB (`salvo_history`).

## Labeling contract

On **COMMIT & VERIFY**, the API persists:

- `verified: true`
- `manual_origin` — operator-selected origin (training label)
- `trajectories[0].origin` — same label for runtime matching
- `verified_at` — ISO timestamp
- `origin_ml_scores` — optional snapshot from suggest-origin

Live origin ML reads `get_verified_history()` (`verified: true` + populated trajectories). **newsFlash** rows are audit-only and are not used for origin ML.

## Workflow

1. Filter queue: Needs review / Multi-origin / Low ML confidence.
2. Select an event — ML scores load from `POST /api/history/suggest-origin`.
3. Confirm or change origin, drag marker if needed, **COMMIT & VERIFY**.
4. **Export** downloads verified training JSON (`GET /api/history/training-export`).

Requires `VITE_MISSION_KEY` matching backend `MISSION_KEY` (copy from `history-fixer/.env.example`).

## Run locally

1. Start backend: `cd backend` then `.\.venv\Scripts\python.exe src/main.py` (listens on 8080).
2. Copy `.env.example` to `.env` and set `VITE_MISSION_KEY`.
3. `npm install` && `npm run dev` — opens **http://127.0.0.1:5174** (proxies `/api` to 8080).

If the sidebar is empty, check the red error panel: usually backend not running or wrong API URL.

Do not set `VITE_API_URL` while using `npm run dev` with a local backend — it skips the Vite proxy.

**Production static build:** set `VITE_API_URL` in `.env.production` only.
