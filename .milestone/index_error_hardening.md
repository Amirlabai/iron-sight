# Historical Trajectory Hardening (MISSION: INDEX_ERROR_HARDENING)

Hardening the TrackingEngine to prevent `IndexError` crashes when processing historical records without valid trajectory data.

## Tactical Scope & Rationale
The current `TrackingEngine._lookup_historical_match` implementation assumes every verified historical record contains a non-empty `trajectories` array. However, drone alerts and certain sparse missile salvos are persisted with empty trajectory lists. This inconsistency triggers internal `IndexIndexError: list index out of range` and destabilizes subsequent ballistic analysis.

## Proposed Technical Changes

### Backend Engine Layer
#### [MODIFY] [engine.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/engine.py)
- **Hardened Trajectory Access**: In `_lookup_historical_match`, implemented explicit checks for `item.get("trajectories")` to ensure index `0` is safe to access.
- **Graceful Lookup Fallback**: If a historical match is found but lacks trajectory data, the engine now skips that record instead of crashing, allowing it to proceed to traditional vectorial analysis.
- **Sync Status Logging**: Updated `_sync_verified_history` to log a warning if zero valid historical records are loaded, aiding in tactical diagnostics.

### Database Persistence Layer
#### [MODIFY] [mongo_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/db/mongo_manager.py)
- **High-Fidelity Verified Fetch**: Optimized `get_verified_history` to explicitly filter for documents where `trajectories` is populated and contains at least one entry.
- **Query Hardening**: Integrated `{"trajectories.0": {"$exists": True}}` into the MongoDB find query across both missile and drone collections to minimize memory overhead from invalid records.

## Verification & Hardening Plan

### Automated Validation
- Execute `scratch/test_index_fix.py` to simulate a pipeline match against a record with `trajectories: []`.
- Validate zero regressions in `ThreatProcessor` logic.

### Manual Intelligence Check
- Trigger a mock drone alert via the tactical simulator and verify the backend logs remain clean of `IndexError` tracebacks.
- Verify through MongoDB Compass that history fetches remain high-fidelity.

---

## Implementation Record

Completed: 2026-04-16

### Changes Deployed

| File | Change |
|---|---|
| `engine.py` | Implementation of defensive guard clauses for safe trajectory array access in historical matching. |
| `mongo_manager.py` | Integration of `trajectories.0` existence filter in verified history retrieval query. |

### Summary

The tracking engine's historical lookup was hardened by implementing explicit non-null check for trajectory arrays before indexing. This was synchronized with a database-level optimization that filters out records lacking valid trajectory data (primarily drone alerts), ensuring the engine only processes high-fidelity historical matches.

