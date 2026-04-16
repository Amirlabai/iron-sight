# Tactical Cluster Shape Expansion (MISSION: CLUSTER_INFLATION)

Implement configurable hull expansion (inflation) to improve tactical visibility. Drones will receive a 50% expansion to encapsulate flight paths, while missiles will receive a subtle 25% expansion for visual emphasis.

## Tactical Rationale
The current convex hull implementation tightly bounds alert cities, leading to "stiff" visual markers that sometimes obscure the underlying threat markers. Inflating the hull provides a tactical buffer that improves readability and UI immersion.

## Proposed Changes

### Configuration Layer
#### [MODIFY] [config.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/config.py)
- **New Constants**:
    - `DEFAULT_INFLATION_FACTOR = 1.0`
    - `DRONE_INFLATION_FACTOR = 1.5` (50% expansion)
    - `MISSILE_INFLATION_FACTOR = 1.25` (25% expansion)

### Core Engine Layer
#### [MODIFY] [engine.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/engine.py)
- **`get_inflated_hull(points, factor)`**: Implementation of the centroid-anchor inflation algorithm.
    - If `factor == 1.0`, falls back to standard `get_convex_hull`.
    - Otherwise, projects hull vertices outward from the cluster centroid by the specified scalar.

### Threat Processing Layer
#### [MODIFY] [threat_processor.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/threat_processor.py)
- **`_build_unified_cluster`**: Updated to accept an optional `factor` argument.
- **`_process_missiles`**: Injects `MISSILE_INFLATION_FACTOR` into all hull calculations.
- **`_process_drone`**: Injects `DRONE_INFLATION_FACTOR` into all hull calculations.

### Tactical Utilities
#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- **`recalculate_unified_metadata`**: Aligned to use a 1.5 variable instead of hardcoded 1.5 (for consistency).
- **`merge_event_group`**: Updated to resolve category-specific inflation factors during multi-alert unification.

## Verification Plan

### Automated Validation
- **Visual Mock**: Generate a mock drone alert with 3 cities and verify the returned `hull` coordinates are ~1.5x further from the centroid than the input cities.
- **Missile Mock**: Repeat for missiles with 1.25x scalar.

### Manual Intelligence Check
- Deploy to tactical dashboard and verify cluster "blooms" to the desired size.
- Verify that News Flash remains un-inflated as per Boss Man's current directive.

---

## Implementation Record

Completed: 2026-04-16

### Changes Deployed

| File | Change |
|---|---|
| `config.py` | Added `DEFAULT_INFLATION_FACTOR`, `DRONE_INFLATION_FACTOR`, `MISSILE_INFLATION_FACTOR` constants |
| `engine.py` | Added `get_inflated_hull(points, factor)` method with centroid-anchor scaling |
| `threat_processor.py` | Wired `MISSILE_INFLATION_FACTOR` (1.25x) into missile hulls, `DRONE_INFLATION_FACTOR` (1.5x) into drone hulls, parameterized `_build_unified_cluster` |
| `cluster_utils.py` | Parameterized `recalculate_unified_metadata` inflation, added category-aware factor resolution in `merge_event_group` |

### Summary

Implemented centroid-anchor hull inflation across the full pipeline. The algorithm computes the standard convex hull first, then scales each vertex outward from the centroid by the category-specific factor. A factor of 1.0 short-circuits to the original hull for zero overhead (newsFlash, earthquakes, infiltrations). The hardcoded 1.5 in `recalculate_unified_metadata` was replaced with the configurable parameter to maintain consistency across all hull computation paths.
