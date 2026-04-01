# IRON SIGHT: TACTICAL CONTEXT (v0.5.5)

> [!IMPORTANT]
> **SOURCE OF TRUTH DIRECTIVE**: Before modifying ANY communication logic (Headers, Endpoints, JSON payloads), you MUST read the [STRATEGIC COMMUNICATION PROTOCOL (SCP)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md) immediately. For UI changes, color palettes, or component architecture, you MUST read the [UI DESIGN SPECIFICATION (TDS)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/UI_DESIGN_SPEC.md) first. Failure to adhere to these protocols will result in Strategic De-sync or UI Degradation.

## MISSION OVERVIEW
Iron Sight is a real-time, strategic intelligence engine designed to detect, analyze, and visualize tactical threats in the Israeli theater. 
It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## KEY MISSION COMPONENTS
- **`backend/` (Command Center)**: Standalone Python 3.12 tactical engine.
    - **Threat Processor**: 10km spatial clustering for unified target zones.
    - **Trajectory Engine**: Normalized 2D PCA vectoring with **Strategic Calculation Borders** for drift-resistant origin detection.
    - **Geodata Store**: Dual-tier boundary system (`tactical_borders.json` for visuals, `calculation_borders.json` for logic). 
    - **Border Utility**: `border_utils.py` for CLI-based `txt` <-> `json` synchronization and coordinate reversal.
    - **Relay Bridge (Israel-Based Source)**: High-fidelity Node.js Scout (`63.250.61.251`) for 403 bypass.
- **Database**: MongoDB Atlas (M0)
- **Deployment**: Render (Backend) / Vercel (Frontend) / Kamatera (Relay)
- **`dashboard/` (Intelligence Dashboard)**: Premium Vite + React command interface.
    - **Map Dynamics**: Leaflet-driven strategic view with Origin-to-Israel corridor auto-centering.
    - **Tactical Silhouettes**: 360° high-res 4K-Tactical border rendering (`tactical_geodata.js`).
    - **Mission Archive**: Historical rewind and playback telemetry synchronized with backend logs. Streamlined observer-only interface.
    - **Aesthetics**: Military-grade Glassmorphic UI with responsive glows and **calibrated radar scans**.

## ALPHA DEVELOPMENT FOCUS (S4)
Transitioned to v0.5.5 (Alpha).

### RECENT OPERATIONS
- **Uplink Consolidation**: Established the Israeli Relay Bridge as the sole tactical uplink.
- **Protocol Alignment**: Standardized all cross-system communication via the [SCP](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md).
- **Tactical Filtering**: Implemented `type: newsFlash` and `instructions`-based ignore logic for "End of Threat" status messages.
- **Active Salvo Persistence**: Extended backend WebSocket manager to buffer and transmit current `active_salvo_data` to synchronize late-joining dashboard clients.
- **Relay Payload Lexicon**: Saved for future implementation:
    - `missiles`
    - `earthQuake`
    - `hostileAircraftIntrusion`
    - `newsFlash` (Status Update / Threat End)
    - `terroristInfiltration`
