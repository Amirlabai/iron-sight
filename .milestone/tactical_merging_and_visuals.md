# MISSION: Tactical Intelligence & Visual Hardening

Enhance the Iron Sight backend with intelligent alert merging and granular threat termination, while upgrading the drone intercept visuals for a more premium, high-fidelity experience.

## User Review Required

> [!IMPORTANT]
> **Merge Proximity Threshold**: I propose a 15km threshold for proximity-based merging. Boss Man, does this sound calibrated for tactical clustering?
> **Visual vs Backend State**: Events will remain separate in the backend's `active_events{}` to maintain lifecycle integrity, but will be broadcast as unified clusters in the `multi_alert` payload for dashboard clarity.

## Proposed Changes

### [Component] Backend Core Logic
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Granular Termination**: Update `newsFlash` handling to parse instructions for cities and regions (e.g., "מחוז אילת"). Cross-reference with `lamas_data.json` to identify and terminate specific subsets of `active_events`.
- **Intelligent Broadcast**: Refactor `_broadcast_multi_alert` to implement merging logic:
    - **Subset Rule**: If Event A's cities are a subset of Event B, merge A into B.
    - **Proximity Rule**: If Event A and B share the same category and their centroids are within the tactical threshold, merge them.

#### [NEW] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- Implementation of the merging logic and set-based subset detection.
- Proximity calculation using Haversine distance.

### [Component] Intelligence Dashboard
#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- **`TrackingDrone` Upgrade**:
    - Refactor the drone marker to include a "trailing tail" effect.
    - Implement rounded corners on the drone shape.
    - Ensure movement strictly follows the provided coordinate array without excessive smoothing that deviates from the flight path.

#### [MODIFY] [App.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.css)
- Add styles for the new drone components: `.drone-tail`, `.drone-body-premium`.
- Enhance glows and animations for aircraft intrusions.

## Verification Plan

### Automated Tests
- **Simulator Stress Test**: Run a simulation with three overlapping drone alerts to verify the merge logic groups them correctly in the UI.
- **Termination Test**: Trigger a `newsFlash` for "Gush Dan" and verify only threats in that region are purged.

### Manual Verification
- Observe the `TrackingDrone` on the map across multiple waypoints to confirm the "tail" follows the path accurately.
- Verify that merged visuals still allow the backend to terminate one part of a cluster while the other remains active (Subset Persistence).

---

## Implementation Record

Completed: 2026-04-02

### Changes Deployed

| File | Change |
|---|---|
| `cluster_utils.py` | Added implementation for bounding logic, Haversine proximity, and subset detection. |
| `main.py` | Overhauled _broadcast_multi_alert to use merging payloads. Added granular subset termination via newsFlash checking. |
| `App.jsx` | Restructured `TrackingDrone` HTML payload with distinct containers for body and tail. |
| `App.css` | Implemented `.drone-body-premium` and `.drone-tail` styles using linear gradients and glass effects. |

### Summary

The tactical system now performs intelligent grouping prior to socket broadcast using the subset rule and 15km threshold proximity rule to optimize visual fidelity and reduce UI clutter, while preserving explicit lifecycle integrity on the backend. Drone interfaces were reconfigured with premium CSS-rendered bodies with trailing gradient sweeps, greatly improving tactical immersion.
