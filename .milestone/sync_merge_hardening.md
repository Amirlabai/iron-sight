# Sync and Merge Hardening (MISSION: SYNC-HARDEN-S1)

Resolve the "Refresh Gap" by unifying the Late-Joiner Sync logic with the live merger, and implement Cluster-Aware Timeouts to keep unified alerts alive during sparse rolling updates.

## Proposed Changes

### Tactical API Layer
#### [MODIFY] [ws_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/api/ws_manager.py)
- Import `build_merged_payloads` from `src.utils.cluster_utils`.
- Update `ws_handler` to call `build_merged_payloads(self.active_events, self.engine)` for the initial `multi_alert` sync.
- This ensures that a refresh immediately shows the same merged view as the live stream.

### Tactical Engine Layer
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Cluster-Aware Timeout Extension**: When a `ROLLING_UPDATE` is processed for a specific `alert_id`, identify all other `active_events` that are currently merged with it (using the 15km/subset logic).
- Reset the `last_update_time` for the entire group. This prevents members of a merged cluster from timing out prematurely while the main event is still active.

### Utility Layer
#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- Refactor `build_merged_payloads` to expose a helper function that returns the adjacency groups (clusters) without the full payload transformation.
- This will be used by `main.py` to identify "Cluster Members" for time synchronization.

## Verification Plan

### Automated Tests
- **Sync Audit**: Manually trigger two overlapping simulated alerts via the sandbox, then refresh the dashboard. Verify the map shows ONE merged cluster immediately upon reload.
- **Timeout Test**: Simulate a drone cluster with two IDs. Keep one ID updated and let the other idle. Verify both stay alive on the map as long as the cluster receives updates.

### Manual Verification
- Visual check: Confirm the "MERGE_DETECTED" logs trigger on initial connection if active events exist.
---

## Implementation Record

Completed: 2026-04-06

### Changes Deployed

| File | Change |
|---|---|
| `ws_manager.py` | Integrated `build_merged_payloads` for Late-Joiner sync parity. |
| `main.py` | Implemented `CLUSTER_TIMEOUT_SYNC` for unified event expiration. |
| `cluster_utils.py` | Exposed `get_cluster_groups` helper for timeout synchronization. |

### Summary

Successfully resolved the "Refresh Gap" by unifying the WebSocket initial sync logic with the live merging pipeline. The introduction of Cluster-Aware Timeouts ensures that all members of a merged tactical group expire simultaneously, preventing visual fragmentation during sparse rolling updates.
