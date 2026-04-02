#include <.context/COMMUNICATION_PROTOCOL.md>
#include <.context/UI_DESIGN_SPEC.md>

# IRON SIGHT: TACTICAL CONTEXT (v0.8.0)

> [!IMPORTANT]
> **SOURCE OF TRUTH DIRECTIVE**: Before modifying ANY communication logic (Headers, Endpoints, JSON payloads), you MUST read the [STRATEGIC COMMUNICATION PROTOCOL (SCP)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md) immediately. For UI changes, color palettes, or component architecture, you MUST read the [UI DESIGN SPECIFICATION (TDS)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/UI_DESIGN_SPEC.md) first. Failure to adhere to these protocols will result in Strategic De-sync or UI Degradation.

## MISSION OVERVIEW
Iron Sight is a real-time, strategic intelligence engine designed to detect, analyze, and visualize tactical threats in the Israeli theater. 
It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## KEY MISSION COMPONENTS
- **`backend/` (Command Center)**: Modular Python 3.12 tactical engine (`src/` architecture).
    - **`src/core/`**: Unified-cluster analysis (no DBSCAN), PCA vectoring, and multi-threat processing (`missiles`, `hostileAircraftIntrusion`, `terroristInfiltration`, `earthQuake`).
    - **`src/api/`**: WebSocket synchronization and REST handlers for history/cities.
    - **`src/db/`**: Multi-collection persistence for isolated threat archives.
    - **Geodata Store**: Dual-tier boundary system (`tactical_borders.json` for visuals, `calculation_borders.json` for logic). 
    - **Relay Bridge (Israel-Based Source)**: High-fidelity Node.js Scout (`63.250.61.251`) for 403 bypass.
- **Database**: MongoDB Atlas (M0)
- **Deployment**: Render (Backend) / Vercel (Frontend) / Kamatera (Relay)
- **`dashboard/` (Intelligence Dashboard)**: Premium Vite + React command interface.
    - **Map Dynamics**: Leaflet-driven strategic view with Origin-to-Israel corridor auto-centering.
    - **Tactical Silhouettes**: 360° high-res 4K-Tactical border rendering (`tactical_geodata.js`).
    - **Mission Archive**: Historical rewind and playback telemetry synchronized with backend logs. Streamlined observer-only interface.
    - **Aesthetics**: Military-grade Glassmorphic UI with responsive glows and **calibrated radar scans**.

## ALPHA DEVELOPMENT FOCUS (S5)
Transitioned to v0.8.0 (Alpha).

### RECENT OPERATIONS
- **Uplink Consolidation**: Established the Israeli Relay Bridge as the sole tactical uplink.
- **Protocol Alignment**: Standardized all cross-system communication via the [SCP](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md).
- **Reset Protocol Hardening**: Shortened dashboard reset delay to 10s for explicit "Event Ended" signals, with immediate backend state purging.
- **Cluster-Based Iran Filtering**: Applied a dual-tier threshold system (`MIN_IRAN_THRESHOLD=10`, `MAX_IRAN_THRESHOLD=40`) to map massive salvos explicitly to Iran while demoting sparse clusters to regional origins.
- **Tactical Console Hardening (v0.5.5)**: 
    - Masked backend infrastructure via Vercel `/api` rewrites, anonymizing REST traffic.
    - Eliminated diagnostic console warnings (`MISSION_SYNC_TIMEOUT`) and sanitized production logs.
    - Integrated `IS_PROD` environment detection for silent telemetry.
- **Backend Modernization (v0.7.0)**:
    - Migrated to professional `src/` modular architecture.
    - Integrated multi-threat logic for drones, infiltrations, and seismic alerts.
    - Implemented category-aware visual orchestration (`TrackingDrone` JS Interpolation).
    - Established independent MongoDB collection archives for threat separation.
- **ID-Driven Architecture (v0.8.0)**:
    - Replaced scalar `last_alert_id`/`active_salvo` with `active_events{}` dictionary keyed by alert ID.
    - Simulator refactored to message queue with per-ID dispatch/cancellation and top-left hovering icons.
    - Stripped DBSCAN clustering from `threat_processor.py`. All cities per ID form one unified cluster.
    - Backend broadcasts `multi_alert` payloads; dashboard renders simultaneous threats via `liveEvents[]` array.
    - End signals target specific IDs or broadcast to all active events with 10s grace period.
    - Lifecycle hardening: replaced `start_time` timeout with `last_update_time` inactivity timeout (5 min silence).
    - Mandatory detection logging: DETECTION_SIGNAL, ROLLING_UPDATE, EVENT_TIMEOUT, EVENT_PERSISTED, EVENT_PURGED.
