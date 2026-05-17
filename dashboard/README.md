# IRON SIGHT | Tactical Dashboard (Frontend)

The frontend for **Iron Sight** is a high-performance, mobile-hardened React application designed for sub-second situational awareness. It prioritizes data density, visual clarity, and rapid tactical interaction.

## Documentation (read before UI changes)

| Doc | Purpose |
|-----|---------|
| [`.context/MOBILE_SHELL_SPEC.md`](../.context/MOBILE_SHELL_SPEC.md) | **Mobile/desktop shell contract** — peek, drag, header, boot. Do not override during bug fixes. |
| [`.context/UI_DESIGN_SPEC.md`](../.context/UI_DESIGN_SPEC.md) | Colors, typography, module aesthetics |
| [`REVIEW-STATUS.md`](../REVIEW-STATUS.md) | UX audit checklist (done vs open) |
| [`context.md`](../context.md) | Project-wide tactical context |

## Key Features

- **Live Tactical Overlay**: Interactive map displaying real-time threat clusters, hulls, and launch trajectories.
- **Strategic History Mode**: Toggle between "Live" and "Timeframe" modes to analyze historical salvos with smart polygon merging.
- **Tactical Sidebar**:
    - **Live Feed**: Chronological list of active threats with expandable city details.
    - **Mission Stats**: Real-time counts of active clusters and target zones.
    - **Control Panel**: Filter by threat category, timeframe, and cluster-merging preference.
- **Mobile shell (≤1024px)**:
    - **Collapsed:** drag pill only — no tabs in peek; drag up to open LIVE | HISTORY | SANDBOX.
    - **Header:** 45px logo/status row; Jerusalem clock floats below the bar on the map.
    - **Sheet:** `position: fixed` to viewport bottom; collapse offset measured from DOM (see spec).
- **Audio Engine**: Directional alert sounds for different threat categories (Missiles, Drones, Infiltrations).

## Technical Stack

- **Framework**: React 19 (Vite)
- **Styling**: Vanilla CSS with a tactical glassmorphism design system.
- **Mapping**: Leaflet + React-Leaflet.
- **Motion**: Framer Motion — bottom sheet uses `useMotionValue` for Y (see MOBILE_SHELL_SPEC).
- **Utilities**:
    - `geoUtils.js`: Custom implementation of the Monotone Chain Convex Hull algorithm.
    - `mapGeometry.js`: Fit padding, archive/timeframe map config.
    - `TacticalProvider.jsx`: WebSocket state, history fetching, `useMemo` timeframe merge.

## Key files (mobile)

| File | Role |
|------|------|
| `src/components/Sidebar/Sidebar.jsx` | Bottom sheet drag, peek measurement |
| `src/styles/layout.css` | Mobile header + sheet CSS (`@media max-width: 1024px`) |
| `src/utils/constants.js` | `MOBILE_LAYOUT_BREAKPOINT`, sidebar ratios |
| `src/App.jsx` | Splash gating, shell mount on `isReady` |
| `src/context/TacticalProvider.jsx` | WS boot, tab change (no auto-expand) |

## Getting Started

1. **Install Dependencies**:
   ```bash
   npm install
   ```
2. **Environment Configuration**:
   Create a `.env` file based on `.env.example`:
   ```env
   VITE_TACTICAL_API_URL=http://localhost:8080
   VITE_WEBSOCKET_URL=ws://localhost:8080/ws
   ```
3. **Run Development Server**:
   ```bash
   npm run dev
   ```

---
**Status**: **DEPLOYED** | See root `version.json` for release tag.
