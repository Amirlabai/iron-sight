# IRON SIGHT MISSION CONTEXT (V3.7 - FULL TACTICAL)

## PROJECT OVERVIEW
`Iron Sight` (V0.0.0) is a high-fidelity tactical radar system for the "Red Alerts Israel" theater. It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## KEY MISSION COMPONENTS
- **`backend/` (Command Center)**: Standalone Python 3.12 tactical engine.
    - **Threat Processor**: 10km spatial clustering for unified target zones.
    - **Trajectory Engine**: Normalized 2D PCA vectoring for straight-line strike axis projection.
    - **Geodata Store**: High-resolution national border silhouettes (`tactical_borders.json`).
    - **Telemetry Broadcast**: WebSocket server (Port 8080) for real-time strategic map framing.
    - **Persistence Layer**: MongoDB Atlas (M0) with `motor` asynchronous driver for mission history.
- **`dashboard/` (Intelligence Dashboard)**: Premium Vite + React command interface.
    - **Map Dynamics**: Leaflet-driven strategic view with Origin-to-Israel corridor auto-centering.
    - **Tactical Silhouettes**: 360° high-res 4K-Tactical border rendering (`tactical_geodata.js`).
    - **Mission Archive**: Historical rewind and playback telemetry synchronized with backend logs.
    - **Aesthetics**: Military-grade Glassmorphic UI with responsive glows and pulse animations.

## STRATEGIC FOCUS
Transitioned to V4.0 (Persistence Era). The mission archive is now decoupled from the ephemeral filesystem, ensuring tactical continuity across cloud restarts. Preparing for final Render deployment.
