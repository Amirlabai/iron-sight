# History Fixer — operator console

Verify salvo origins, step through the origin pipeline (replay tab), and build the ML training corpus in MongoDB (`salvo_history`).

## Labeling contract

On **COMMIT & VERIFY**, the API persists:

- `verified: true`
- `manual_origin` — operator-selected origin (training label)
- `trajectories[0].origin` — same label for runtime matching
- `verified_at` — ISO timestamp
- `origin_ml_scores` — optional snapshot from suggest-origin

## Workflow

1. **Audit** tab: filter queue, select event, ML suggest, drag pin, **COMMIT & VERIFY**, export training JSON.
2. **Pipeline Replay** tab: step through origin determination for the selected missile event (or use **Replay pipeline** from the audit panel).

Requires `VITE_MISSION_KEY` matching backend `MISSION_KEY` (copy from `history-fixer/.env.example`).

## Run locally (recommended)

From repo root:

```powershell
.\scripts\run-operator.ps1
```

Starts:

- Operator API on **http://127.0.0.1:8081** (`python backend/operator_main.py` — Mongo + history/replay routes only, no relay/WS)
- History-fixer UI on **http://127.0.0.1:5174** (Vite proxies `/api` → 8081)

Requires `backend/.env` with `MONGO_URI` and `MISSION_KEY`.

### API only

```powershell
cd backend
.\.venv\Scripts\python.exe operator_main.py
```

### UI only (operator API already running)

```powershell
cd history-fixer
copy .env.example .env
npm install
npm run dev
```

Do not set `VITE_API_URL` in dev — it bypasses the Vite proxy.

**Production static build:** set `VITE_API_URL` in `.env.production` only.
