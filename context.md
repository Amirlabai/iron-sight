# IRON SIGHT MISSION CONTEXT (UNIFIED)

## PROJECT OVERVIEW
`Iron Sight` (V0.3.0) is a high-fidelity tactical radar system for the "Red Alerts Israel" theater. It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

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
Transitioned to v0.3.0 (Alpha). Patched the tactical health check logic and internalized the `list-object` normalization for the Python Backend. Correctly handle empty alert arrays (`[]`) and multi-alert payloads from the integrated proxy scouts. Successfully restored the "Operational" status visibility on the dashboard while maintaining high-fidelity monitoring from the Kamatera-based Node.js relay. Hardened environment security with `RELAY_AUTH_KEY` and updated all tactical configuration layers. Maintained v0.1.1 baseline security (CORS/Mission-Key) and MongoDB Atlas persistence.
