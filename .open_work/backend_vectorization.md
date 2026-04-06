# Backend Vectorization (MISSION: NUMPY-HPOWER)

This mission replaces standard Python `for` loops with vectorized NumPy and SciPy operations to maximize the "Numerical Horsepower" of the Iron Sight engine.

## Proposed Changes

### Tactical Engine Layer
#### [MODIFY] [engine.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/engine.py)
- **Vectorized Clustering**: Replace manual Union-Find in `cluster()` with `scipy.sparse.csgraph.connected_components` for O(N) performance on the distance matrix.
- **Centroid Calculation**: Use pre-converted NumPy arrays for `get_origin` and `get_projected_origin` to eliminate list-of-dict parsing overhead.
- **Projected Origins**: Vectorize the territory containment checks by passing coordinate arrays directly to `_ray_cast_vectorized`.

### Utility Layer
#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- **Integer-Based Subset Masking**: Map the finite set of Israeli cities (~300) to unique integer indices. Replace `set.issubset` with integer bitmask comparisons for O(1) subset detection.
- **Adjacency Discovery**: Refactor `_build_adjacency_components` to use NumPy broadcasting for category matches and optimized masks for proximity, eliminating nested Python loops.
- **Vectorized Haversine**: Ensure all distance calculations leverage the existing `haversine_distance_matrix`.

### Core Lifecycle Layer
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- **Batch Processing**: Ensure `ROLLING_UPDATE` passes NumPy arrays to the processor to minimize conversion overhead during high-frequency updates.

## Verification Plan

### Automated Tests
- **Performance Benchmark**: Measure `TrackingEngine.cluster` latency with 100+ simulated cities (Target: <2ms).
- **Parity Check**: Confirm `scipy.connected_components` exactly matches legacy Union-Find results for complex city overlaps.
- **Mask Accuracy**: Validate bitmask subset logic against the legacy set-based results.

### Manual Verification
- **Stress Test**: Trigger a "Massive Salvo" (40+ cities) in the Sandbox and monitor backend logs for processing speed.
