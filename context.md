# IRON SIGHT MISSION CONTEXT (V3.7 - FULL TACTICAL)

## PROJECT OVERVIEW
`Iron Sight` (V3.5) is a high-fidelity tactical radar system for the "Red Alerts Israel" theater. It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## KEY MISSION COMPONENTS
- **`backend/` (Command Center)**: Standalone Python 3.12 tactical engine.
    - **Threat Processor**: 10km spatial clustering for unified target zones.
    - **Trajectory Engine**: Normalized 2D PCA vectoring for straight-line strike axis projection.
    - **Geodata Store**: High-resolution national border silhouettes (`tactical_borders.json`).
    - **Telemetry Broadcast**: WebSocket server (Port 8080) for real-time strategic map framing.
- **`dashboard/` (Intelligence Dashboard)**: Premium Vite + React command interface.
    - **Map Dynamics**: Leaflet-driven strategic view with Origin-to-Israel corridor auto-centering.
    - **Tactical Silhouettes**: 360° high-res 4K-Tactical border rendering (`tactical_geodata.js`).
    - **Mission Archive**: Historical rewind and playback telemetry synchronized with backend logs.
    - **Aesthetics**: Military-grade Glassmorphic UI with responsive glows and pulse animations.

## STRATEGIC FOCUS
Transitioned to V3.7 (Full Tactical Visibility). All geographic boundaries are now permanently rendered at 30FPS, providing 24/7 situational awareness across all strategic corridors. Preparing for final cloud deployment.
