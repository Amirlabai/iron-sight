# Tactical History Merging (MISSION: HISTORY-MERGE-HARDENING)

The objective is to unify clustered alerts into a single history entry in MongoDB. Currently, alerts are processed by ID and saved individually upon expiration, even if they were visually merged in the dashboard. This fragmentation prevents the history archive from representing the true scope of major tactical events.

## Tactical Scope & Rationale
Fragmentation occurs because the backend lifecycle treats each alert ID as an independent unit. While the dashboard visually merges them via `build_merged_payloads`, the persistence layer saves each member of a cluster separately. This results in a "noisy" history panel with redundant entries for the same tactical event.

## Proposed Technical Changes

### Cluster Utilities
#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- **Flexible Adjacency Build**: Refactor `_build_adjacency_components` to accept a generic list of items for easier logic reuse.
- **State-Independent Merging**:
    - `group_events(events_dict, threshold_km=15)`: Extract core grouping logic into a standalone function that works regardless of `end_time`.
    - `merge_event_group(group_ids, events_dict, engine)`: Merges a specific set of IDs into a single consolidated payload.
    - `get_cluster_groups(active_events, include_all=False)`: Parametrize the active-only filter.

### Backend Lifecycle
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Cluster-Aware Persistence**:
    - Refactor the "Lifecycle Maintenance" loop.
    - Get all event groups using `group_events(active_events)`.
    - For each group:
        - Identify if **all** members have an `end_time` set.
        - Trigger persistence if **at least one** member has exceeded the 10-second grace period.
- **Consolidated Batch Operations**:
    - Call `db.save_alert` once for the merged Master Payload.
    - The Master Payload uses the lexicographically first ID and contains `merged_ids: [ID1, ID2, ...]`.
    - Simultaneously purge all IDs in the group from `active_events` and log `EVENT_PURGED`.

### Database Layer
#### [MODIFY] [mongo_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/db/mongo_manager.py)
- **High-Fidelity Persistence**: Ensure `save_alert` properly handles the `merged_ids` field.
- **Audit Logs**: Enhanced logging for `CLUSTER_PERSISTED: [ID1, ID2...] -> Master_ID`.

## Verification & Hardening Plan

### Automated Validation
- **Simulated Salvo**: Trigger 5 geographically overlapping IDs via a test relay/script.
- **DB Check**: Verify exactly **one** entry in the respective threat collection (e.g., `missiles`).
- **Log Audit**: Verify all 5 IDs reach `PURGED` state in `event_logs` at the same timestamp.

### Manual Intelligence Check
- **History Exploration**: Open the history panel in the dashboard. Confirm that events occurring within the same tactical window are represented by a single, expandable record showing the unified impact area.
