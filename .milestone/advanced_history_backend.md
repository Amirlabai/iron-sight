# Advanced History: Backend Aggregation (MISSION: HISTORY-ADV-BACKEND)

This mission unifies all tactical threat categories into a single, consolidated history stream to support comprehensive intelligence archiving.

## Proposed Changes

### Tactical Database Layer

#### [MODIFY] [mongo_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/db/mongo_manager.py)
- **Unified Query Architecture**: Implement `get_consolidated_history()` to perform parallel fetches across `missiles`, `hostileAircraftIntrusion`, `terroristInfiltration`, and `earthQuake` collections.
- **Chronological Sorting**: Ensure all results are unified and sorted by timestamp/ID before returning to the API layer.

### Tactical API Layer

#### [MODIFY] [ws_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/api/ws_manager.py)
- **Uplink Synchronization**: Update the WebSocket `on_open` sync to push the consolidated history by default.
- **REST Filter Support**: Enhance `history_handler` to support a `?category=` query parameter for granular filtering from the dashboard.

#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Lifecycle Broadcast**: Trigger a full consolidated history broadcast upon any event persistence (EVENT_PERSISTED) to keep all participants synchronized.

## Verification Plan

### Automated Tests
- **Consolidation Parity**: Script to populate multiple collections and verify that `get_consolidated_history` returns the correct interleaved sequence.
- **API Response**: Verify `/api/history?category=missiles` vs `/api/history` (all) via `curl`.

### Manual Verification
- **Log Audit**: Trigger a drone alert and a missile alert in succession; verify both appear in the backend history broadcast log.
