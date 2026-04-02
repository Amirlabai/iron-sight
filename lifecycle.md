# Alpha Hardening: ID-Driven Multi-Threat Lifecycle (v0.8.0)

The objective is to resolve the strategic "skipped alerts" failure identified in the logs by hardening the v0.8.0 ID-driven engine. This involves fixing the static timeout bug that causes active events to be purged early and implementing mandatory detection logging so no alert (like a 200-city update) passes through the system silently.

## User Review Required

> [!IMPORTANT]
> **LIFECYCLE CHANGE**: The 5-minute timeout is currently based on the **start time** of the event. This means any event lasting longer than 5 minutes is forcibly terminated even if it's receiving updates. I am changing this to a **"Last Update" timeout**, meaning an alert will only end after 5 minutes of total silence.

---

## Proposed Changes

### Tactical Engine & Lifecycle

#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Lifecycle Optimization**: Replace static `start_time` with `last_update_time` (or update it) to ensure events ONLY timeout after 5 minutes of **inactivity**, not 5 minutes of total lifespan.
- **Mandatory Reporting**: Add `logger.info` for:
  - Initial threat detection (ID, Category, City Count).
  - Rolling updates (ID, New Cities detected).
- **Graceful Termination**: Ensure `end_time` logic properly triggers DB persistence for both targeted newsFlash signals and involuntary timeouts.
- **Protocol Guard**: Robustly handle both `alert_payload.get('data')` and `alert_payload.get('cities')` to prevent data loss from relay library variances.

#### [MODIFY] [version.json](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/version.json)
- **Version Bump**: Advance to `v0.8.0` to match the strategic ID-driven architecture and consistent dashboard reporting.

### Database Persistence

#### [MODIFY] [mongo_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/db/mongo_manager.py)
- **ID-Based Upsert**: Ensure `save_alert` uses the unique `id` for upsertion, allowing the 200-city merge to effectively update the historical record in MongoDB rather than creating fragmented entries or skipping updates.

---

## Open Questions

- **Do you want to keep the 5-minute silence timeout?** Or should it be shorter (e.g., 2 minutes) for faster dashboard recovery if a signal is lost?

---

## Verification Plan

### Automated Verification (Simulator)
- **Multi-Alert Merge Test**:
  1. Dispatch 10-city alert `test_id_1`.
  2. Dispatch 200-city alert `test_id_1` (merge).
  3. Verify backend logs `DETECTION_SIGNAL` and `ROLLING_UPDATE`.
  4. Verify MongoDB has the single 210-city entry.
- **Timeout Persistence Test**:
  1. Dispatch alert and wait for timeout.
  2. Verify backend logs `EVENT_PURGED_BY_TIMEOUT` and DB save success.

### Manual Verification
- Monitor the backend console to confirm the new high-fidelity logging captures all events from the Israeli relay.
