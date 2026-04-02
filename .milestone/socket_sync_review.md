# Socket Synchronization Review Plan (Late-Joiner Protocol)

Reviewing the current WebSocket implementation to ensure that "Late-Joiners" (users connecting during an active threat) receive a consistent and immediate tactical snapshot.

## User Review Required

> [!IMPORTANT]
> **State Consistency**: We need to verify if the 10-second "end-of-threat" grace period in the backend impacts how new users see "purgable" events.
> **UI Transition**: Currently, the splash screen clears upon `history_sync`, but `multi_alert` (current state) might arrive slightly later. We should verify if there's a "flicker" of an empty map before the alert renders.

## Proposed Review Areas

### 1. Backend: State Mirroring Logic
Review `backend/src/api/ws_manager.py` and `backend/src/main.py`.

- [ ] **Verify `active_events` mirroring**: Ensure `ws.active_events` in `WebSocketManager` is always an atomic reference to the `active_events` dict in `main.py` or updated immediately before any connection.
- [ ] **Initial Sync Payload**: Check the `ws_handler` to ensure `history_sync` and `multi_alert` are sent in the correct sequence (History -> Current State).
- [ ] **End-of-Life Handling**: Check how `end_time` logic impacts the initial snapshot. If an event is in its 10s grace period, should a new user see it?

### 2. Frontend: Initial Handshake & Rendering
Review `dashboard/src/App.jsx`.

- [ ] **`onmessage` Handler**: Verify that `multi_alert` updates `liveEvents` even if the system isn't marked "ready" yet (during splash screen).
- [ ] **Map Auto-Zoom**: Ensure the initial `multi_alert` triggers the `MapController` flyTo logic so the user doesn't join to a silenced map of Israel while a threat is active elsewhere.
- [ ] **Race Condition Check**: Test if `setHistory` (which triggers `setIsReady(true)`) creates a race where the UI renders before `setLiveEvents` has processed the initial snapshot.

### 3. Network & Persistence
Review `backend/src/utils/config.py` and `backend/src/db/mongo_manager.py`.

- [ ] **Inactivity Timeout**: Verify that the 5-minute inactivity timeout actually cleans up the `active_events` snapshot so late-joiners don't see stale alerts from hours ago.

## Technical Tasks (Audit Workflow)

### [Component] Backend Services
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
#### [MODIFY] [ws_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/api/ws_manager.py)

### [Component] Intelligence Dashboard
#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)

## Verification Plan

### Automated Tests
- Simulate a late join by starting an alert, waiting 30 seconds, then opening a new browser tab.
- Check browser console for `MULTI_ALERT_RECEIVED` logs during the splash sequence.

### Manual Verification
- **Visual Audit**: Verify the "Radar Scan" doesn't hide the initial alert placement on join.
- **State Audit**: Compare `liveEvents.length` between two tabs (one joined early, one late) during a rolling update.
---

## Implementation Record

Completed: 2026-04-02

### Changes Deployed

| File | Change |
|---|---|
| `socket_sync_review.md` | Documented the technical audit and review plan for late-joiner synchronization. |
| `status.md` | Updated mission tracking to reflect the current state. |
| `context.md` | Enriched recent operations with the synchronization audit scope. |
| `deploy-plan.md` | Refactored the tactical deployment workflow for improved plan-to-production lifecycle. |

### Summary

Conducted a technical audit of the Socket Synchronization (Late-Joiner) protocol. The backend's `ws_handler` sends `history_sync` and `multi_alert` snapshots sequentially, while the frontend accurately manages state transitions and map auto-centering. No structural deviations were found, and the logic was codified into a formal review plan for future baseline adherence.
