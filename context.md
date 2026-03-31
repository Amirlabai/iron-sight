# IRON SIGHT MISSION CONTEXT (UNIFIED)

## PROJECT OVERVIEW
`Iron Sight` (V0.3.2) is a high-fidelity tactical radar system for the "Red Alerts Israel" theater. It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## KEY MISSION COMPONENTS
- **`backend/` (Command Center)**: Standalone Python 3.12 tactical engine.
    - **Threat Processor**: 10km spatial clustering for unified target zones.
    - **Trajectory Engine**: Normalized 2D PCA vectoring with **Strategic Calculation Borders** for drift-resistant origin detection.
    - **Geodata Store**: Dual-tier boundary system (`tactical_borders.json` for visuals, `calculation_borders.json` for logic).
    - **Relay Bridge (Israel-Based Source)**: High-fidelity Node.js Scout (`63.250.61.251`) for 403 bypass.
- **Database**: MongoDB Atlas (M0)
- **Deployment**: Render (Backend) / Vercel (Frontend) / Kamatera (Relay)
- **`dashboard/` (Intelligence Dashboard)**: Premium Vite + React command interface.
    - **Map Dynamics**: Leaflet-driven strategic view with Origin-to-Israel corridor auto-centering.
    - **Tactical Silhouettes**: 360° high-res 4K-Tactical border rendering (`tactical_geodata.js`).
    - **Mission Archive**: Historical rewind and playback telemetry synchronized with backend logs. Streamlined observer-only interface.
    - **Aesthetics**: Military-grade Glassmorphic UI with responsive glows and **calibrated radar scans**.

## ALPHA DEVELOPMENT FOCUS
Transitioned to v0.4.2 (Alpha). Stabilized the tactical uplink by resolving field name mismatches between the backend and frontend ('relay_scout' -> 'upstream_source'), ensuring the 'LIVE INTERCEPT' status correctly displays on the dashboard. Hardened the relay with PM2 process awareness and root health-check routes for enhanced recovery.
