# Origin Replay — Iron Sight Dev Tool

Step-through debugger for the missile origin determination pipeline. Pick an archived salvo, then advance through each algorithm stage (clustering, historical match, vector projection, ML tie-break) with map visuals.

## Prerequisites

- Backend running on port 8080 (`IRON_SIGHT_DEV=1` recommended for local work)
- MongoDB with missile archive data (`salvo_history`)
- Mission key matching backend `MISSION_KEY` (default in `.env.example`)

## Setup

```powershell
cd origin-replay
copy .env.example .env
npm install
npm run dev
```

Opens at http://localhost:5175 (Vite proxies `/api` → `http://127.0.0.1:8080`).

## Usage

1. Select a missile event from the archive list (search by ID, origin, or city count).
2. Use **Prev / Next** or arrow keys to step through pipeline stages.
3. Toggle **allow_strategic** to replay with or without Iran/Yemen projection gate.
4. On the final step, compare replay origin vs stored archive origin.

## API

`POST /api/origin/replay` (requires `X-Mission-Key` header)

```json
{
  "id": "<alert_id>",
  "category": "missiles",
  "allow_strategic": true
}
```

Returns ordered `steps[]` with map visuals plus `final` payload.

## Related tools

| Tool | Purpose |
|------|---------|
| `history-fixer/` | Verify/correct archived origins, ML suggest, training export |
| `backend/simulator/` | Inject live test alerts (forward-only, not replay) |
| `dashboard/` | Production map UI |
