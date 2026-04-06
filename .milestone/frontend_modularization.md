# Frontend Modularization (MISSION: FE-MODULAR-S1)

Decompose the monolithic `App.jsx` and `App.css` into a professional, component-based architecture using React Context for global state management.

## Proposed Changes

### Core Infrastructure
#### [NEW] [TacticalContext.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/context/TacticalContext.jsx)
- Implement a global provider for `liveEvents`, `viewMode`, `isConnected`, and `tacticalHealth`.
- Centralize state updates to prevent prop-drilling into deeply nested map overlays.

#### [NEW] [constants.js](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/utils/constants.js)
- Extract environment detection, WebSocket URLs, and tactical color tokens.

### Component Layer
#### [NEW] [MapViewer.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/components/Map/MapViewer.jsx)
- Isolated Leaflet container handling the base layer and coordinate synchronization.

#### [NEW] [ThreatOverlay.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/components/Map/ThreatOverlay.jsx)
- Specialized component for rendering trajectories, hulls, and origin pins.

#### [NEW] [Sidebar.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/components/Sidebar/Sidebar.jsx)
- Modular drawer containing the Live, History, and Sandbox panels.

#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- Refactor into a slim top-level orchestrator that wraps the application in the `TacticalProvider`.

### Style Layer
#### [NEW] [layout.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/styles/layout.css)
- Extract high-level grid and flex layouts from the monolithic `App.css`.

#### [NEW] [animations.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/styles/animations.css)
- Centralize the pulse, sweep, and fade-in/out motions.

### Documentation Layer
#### [MODIFY] [UI_DESIGN_SPEC.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.context/UI_DESIGN_SPEC.md)
- Update Section 3 to document the new `TacticalContext` and file hierarchy.

## Verification Plan

### Automated Tests
- `npm run build` from the `dashboard` directory to verify bundle integrity.
- `pip run scripts/export_logs.py` (optional) to ensure no breakage in backend log format.

### Manual Verification
- Visual audit of the Splash Screen timing and transition.
- Verify WebSocket re-connection logic still triggers the "RECONNECTING..." status pill.
- Confirm Audio Mutex still suppresses overlapping missile alerts.

---

## Implementation Record

Completed: 2026-04-06

### Changes Deployed

| File | Change |
|---|---|
| `App.jsx` | Refactored into a 115-line orchestrator using `TacticalContext`. |
| `App.css` | Decomposed into structural and animation-specific stylesheets. |
| `TacticalContext.jsx` | Created global state provider for WebSocket, alerts, and audio. |
| `MapViewer.jsx` | Isolated Leaflet container with coordinate synchronization. |
| `ThreatOverlay.jsx` | Modularized per-event rendering for clusters and trajectories. |
| `Sidebar.jsx` | Implemented modular drawer with mobile drag support. |
| `constants.js` | Centralized environment, geodata, and visual tokens. |
| `UI_DESIGN_SPEC.md` | Updated Section 3 to reflect the new modular architecture. |

### Summary

Successfully decomposed the monolithic frontend into a scalable, context-driven architecture. Significant reduction in file complexity (App.jsx 954 -> 115 lines) improves maintainability and performance. Centralized state via `TacticalContext` eliminates prop-drilling.
