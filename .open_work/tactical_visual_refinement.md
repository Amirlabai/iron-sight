# Tactical Visual Refinement (MISSION: TACTICAL_V_REFINE)

Refine the Iron Sight visual language and intelligence logic based on Boss Man's directives: Unified Vectors, Triangle Drones, and Organic Hulls.

## Proposed Changes

### [Component] Backend Intelligence
#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- Pass the `engine` instance into `build_merged_payloads` to allow access to strategic vectoring utilities.

#### [MODIFY] [cluster_utils.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/utils/cluster_utils.py)
- Update `build_merged_payloads` to perform **Deep Vector Unification**:
    - Use `engine.get_origin()` and `engine.get_projected_origin()` on the aggregated city list.
    - Replace multiple trajectories with a single unified trajectory for `missiles`.

### [Component] Strategic Dashboard
#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- **Rounded Cluster Hulls**: Inject `className="organic-hull"` into the `Polygon` components.
- Adjust `pathOptions` for hulls to include `lineJoin: 'round'` and a heavier stroke weight to provide the "expanded" tactical feel.

#### [MODIFY] [App.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.css)
- **Triangle Drone**: Redefine `.drone-body-premium` using `clip-path: polygon()` to create a sharp triangular wedge.
- **Organic Hulls**: Implement CSS filters for `.organic-hull` to smooth out polygon vertices and add tactical glow.

## Verification Plan

### Automated Tests
- **Vector Audit**: Verify through simulator that two proximity-merged alerts now output exactly ONE unified trajectory.
- **Wedge Orientation**: Confirm the triangular drone nose remains pointed precisely along the flight vector.

### Manual Verification
- Visual inspection of the "Rounded Hulls" on the map—ensuring they look "organic" and modern.
- Confirmation of the new "Triangle" drone morphology.
