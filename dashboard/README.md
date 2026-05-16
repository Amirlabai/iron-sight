# IRON SIGHT | Tactical Dashboard (Frontend)

The frontend for **Iron Sight** is a high-performance, mobile-hardened React application designed for sub-second situational awareness. It prioritizes data density, visual clarity, and rapid tactical interaction.

## 🛡️ Key Features

- **Live Tactical Overlay**: Interactive map displaying real-time threat clusters, hulls, and launch trajectories.
- **Strategic History Mode**: Toggle between "Live" and "Timeframe" modes to analyze historical salvos with smart polygon merging.
- **Tactical Sidebar**:
    - **Live Feed**: Chronological list of active threats with expandable city details.
    - **Mission Stats**: Real-time counts of active clusters and target zones.
    - **Control Panel**: Filter by threat category, timeframe, and cluster-merging preference.
- **Mobile Hardening**: 
    - Optimized 65px interaction zones for pull-up gestures.
    - Condensed header with integrated Tactical Clock.
    - "Return to Live" quick-reset logic.
- **Audio Engine**: Directional alert sounds for different threat categories (Missiles, Drones, Infiltrations).

## 🛠️ Technical Stack

- **Framework**: React 19 (Vite)
- **Styling**: Vanilla CSS with a tactical glassmorphism design system.
- **Mapping**: Leaflet + React-Leaflet.
- **Motion**: Framer Motion for spring-based tactical transitions.
- **Utilities**:
    - `geoUtils.js`: Custom implementation of the Monotone Chain Convex Hull algorithm.
    - `TacticalProvider.jsx`: The central brain managing WebSocket state, history fetching, and smart merging.

## 🚀 Getting Started

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
**Status**: **DEPLOYED** | **v1.0.0**
