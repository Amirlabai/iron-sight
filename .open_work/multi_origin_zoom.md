# Multi-Origin Tactical Zoom & Centering (MISSION: MULTI_ORIGIN_ZOOM)

Ensure the tactical map provides a strategic overview by centering on Israel and using the widest necessary zoom level when threats originate from multiple countries simultaneously.

## Tactical Scope & Rationale
Currently, the map centers on the midpoint of the "priority" trajectory (usually the furthest one). When multiple origins are active (e.g., simultaneous launches from Iran and Lebanon), the map might center on a point in the desert or sea between them, rather than focusing on the target (Israel). This mission implements a strict override: if more than one origin is detected, the map snaps to Israel's center with a zoomed-out strategic view.

## Proposed Technical Changes

### Backend Core & Utils

#### [MODIFY] [threat_processor.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/threat_processor.py)
- **`_process_missiles` logic update**:
  - Calculate `zoom_level` for the alert based on `origin_groups`.
  - If `len(origin_groups) > 1`:
    - Force `cnt` (center) to `[31.7, 35.2]` (Israel).
    - Set `zoom_level` to `min(self.engine.zoom_levels.get(org, 8) for org in origin_groups.keys())`.
  - Else (single origin):
    - Set `zoom_level` to `self.engine.zoom_levels.get(list(origin_groups.keys())[0], 8)`.
  - Inject `zoom_level` into the returned tactical payload.

#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- **`merge_event_group` (Missiles block) update**:
  - Implement the same multi-origin detection logic during event consolidation.
  - Force `base_data["center"] = [31.7, 35.2]` and calculate the minimum `zoom_level` across the merged `origin_groups`.
  - Propagate `zoom_level` to the master payload.

### Dashboard Frontend

#### [MODIFY] [TacticalProvider.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/context/TacticalProvider.jsx)
- **`calculateBestMapConfig` refactor**:
  - Track unique origins across `allTrajectories` (treating `North Iran` and `Iran` as one).
  - If `uniqueOrigins.size > 1`:
    - Return `ISRAEL_CENTER` and the global `minZoom`.
  - Maintain existing logic for single-origin trajectories to preserve localized tactical focus.

## Verification & Hardening Plan

### Automated Validation
- **Simulator Stress Test**: 
  - Trigger a combined "Iran + Lebanon" salvo via the simulator's dispatch dropdown.
  - Verify terminal output for `DETECTION_SIGNAL` or `ROLLING_UPDATE` shows the correct `center` and `zoom_level`.

### Manual Intelligence Check
- Observe the Live Dashboard: ensure the map snap-centers to Israel when multiple origin silhouettes (e.g. red outlines for both Lebanon and Iran) appear simultaneously.
