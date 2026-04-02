# MISSION: Tactical Merging and Visual Restoration (Hardening)

Fix the issues reported by Boss Man regarding the failed alert merging and the uncalibrated drone tail visuals.

## User Review Required

> [!IMPORTANT]
> **Merging Logic Transition**: I am moving from a simple double-nested loop to a recursive grouping algorithm. This ensures that if Alert A matches B, and B matches C, all three are unified into a single visual cluster, even if A and C are beyond the 15km threshold.
> **Drone Tail Calibration**: The tail was previously appearing in front of the drone due to a positioning inversion. I will relocate it to the rear of the flight vector.

## Proposed Changes

### [Component] Backend Processing
#### [MODIFY] [threat_processor.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/threat_processor.py)
- Inject `center` key into the `missiles` alert payload (currently missing, causing proximity checks to fail).

#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- Refactor `build_merged_payloads` to use a recursive grouping strategy.
- Ensure all properties (trajectories, clusters, cities) are deeply aggregated into the lead event of each group.

### [Component] Dashboard Visuals
#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- `TrackingDrone`: Update the `drone-tail` positioning in the `Marker` icon HTML.
- Adjust `iconAnchor` and CSS styles to ensure the "tail" is behind the body.

#### [MODIFY] [App.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.css)
- Refine `.drone-tail` and `.drone-body-premium` styles.
- Change `right: 10px` to a proper `left`-based offset to follow the vector.

## Open Questions

- Boss Man, should the drone tail "flicker" or be a solid tactical sweep? Currently, it's a static gradient trail, but I can add a pulse effect if preferred.

## Verification Plan

### Automated Tests
- **Cluster Regression**: Run the simulator with 3 missile alerts in close proximity and verify they unify on the map.
- **Drone Vector Audit**: Deploy a drone in the simulator and verify the tail remains oriented behind the nose across 90-degree turns.

### Manual Verification
- Visual inspection of the `active_events` logging in the backend console to confirm "MERGE_DETECTED" events (if I add logging).
