# Event Lifecycle Logging (MISSION: LOGGING_STABILIZATION)

Boss Man, we need to track exactly how every threat evolves and terminates to ensure no IDs are missed and the timeout logic is tuned perfectly. This plan outlines the migration to a dedicated MongoDB logging collection.

## Proposed Changes

### Configuration Layer
#### [MODIFY] [config.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/config.py)
- Define `COLLECTION_LOGS = "event_logs"` for centralized lifecycle tracking.

### Database Layer
#### [MODIFY] [mongo_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/db/mongo_manager.py)
- **Initialize `event_logs` collection**: Register the new collection in the `MongoManager` constructor.
- **Implement `log_event(event_id, a_type, status, data=None)`**: A non-blocking method to upsert or append lifecycle steps (DETECTION, UPDATE, TIMEOUT, END_SIGNAL).

### Tactical Engine Layer
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Instrumentation**: Call `db.log_event` at key lifecycle transitions:
    - **Initial Detection**: Log the first appearance of an ID.
    - **Rolling Update**: Log every time new cities are appended.
    - **End Signal**: Log when "האירוע הסתיים" or `newsFlash` targets an ID.
    - **Timeout**: Log when an event is marked for termination due to inactivity.
    - **Purge**: Log the final state before memory cleanup.

## Log Schema Design

Each document in `event_logs` will represent a unique `event_id` lifecycle:

```json
{
  "event_id": "123456789",
  "category": "missiles",
  "is_simulation": false,
  "start_time": "2026-04-02T12:00:00Z",
  "last_update_time": "2026-04-02T12:05:00Z",
  "end_time": "2026-04-02T12:10:00Z",
  "termination_reason": "END_SIGNAL" | "TIMEOUT" | "MANUAL",
  "city_count": 45,
  "city_list": ["Tel Aviv", "Haifa", ...],
  "updates_count": 3,
  "timeline": [
    {"status": "DETECTED", "time": "...", "cities": 10},
    {"status": "UPDATED", "time": "...", "cities": 35},
    {"status": "TERMINATED", "time": "...", "reason": "..."}
  ]
}
```

## Verification Plan

### Automated Tests
- Run `backend/src/main.py` and trigger simulated alerts (via relay or local test script).
- Verify documents are created/updated in MongoDB Atlas under the `event_logs` collection.
- Check `termination_reason` accuracy for both explicit end signals and inactivity timeouts.

### Manual Verification
- Boss Man can check the MongoDB Atlas dashboard to see the live flow of events and their lifecycle history.

---

## Implementation Record

Completed: 2026-04-02

### Changes Deployed

| File | Change |
|---|---|
| `config.py` | Added `COLLECTION_LOGS = "event_logs"` |
| `mongo_manager.py` | Registered `self.event_logs` collection + new `log_event()` method with upsert/timeline-append logic |
| `main.py` | Six `db.log_event()` calls at: DETECTED, UPDATED, END_SIGNAL (targeted), END_SIGNAL (broadcast), TIMEOUT, PURGED |

### log_event() Design

Dual-path upsert approach:
- On `DETECTED`: creates a fresh document with the full schema (event_id, category, timestamps, city data, empty timeline).
- On all other statuses: pushes a timestamped entry to the `timeline[]` array, updates `city_count`/`city_list`, and sets terminal fields (`end_time`, `termination_reason`) when appropriate.

All calls are fire-and-forget with exception handling — they never block or crash the main loop. The `event_logs` collection in MongoDB Atlas auto-creates on first write.
