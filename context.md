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
- **Event Lifecycle Logging (v0.8.1)**:
    - New `event_logs` MongoDB collection via `COLLECTION_LOGS` config constant.
    - `MongoManager.log_event()` upserts lifecycle documents keyed by `event_id` with full timeline arrays.
    - `main.py` instrumented at all five transition points: DETECTED, UPDATED, END_SIGNAL, TIMEOUT, PURGED.
    - Schema tracks `start_time`, `last_update_time`, `end_time`, `termination_reason`, `city_count`, `city_list`, `updates_count`, and chronological `timeline[]`.
- **Socket Synchronization (v0.8.2 - Audit)**:
    - Reviewing Late-Joiner synchronization logic between `ws_manager.py` (Backend) and `App.jsx` (Frontend).
    - Ensuring immediate state mirroring for users joining during active multi-alert events.
    - Plan: [.open_work/socket_sync_review.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/socket_sync_review.md)
- **Tactical Visual Refinement (v0.8.6 - Refinement)**: 
    - Unifying vectors for merged groups, transitioning drones to triangle morphology, and implementing organic/rounded hulls.
    - Plan: [.milestone/tactical_visual_refinement.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/tactical_visual_refinement.md)
- **Tactical Audio Engine (v0.9.0 - Implementation)**:
    - Dedicated audio driver for deduplicated missile alerts (1x) and drone loops (2x).
    - Plan: [.open_work/tactical_audio_engine.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/status.md)
- **Log Export Utility (v0.8.3)**:
    - Implemented `scripts/export_logs.py` for automated extraction of `event_logs` from MongoDB to CSV.
    - Flattens nested `city_list` and serializes `timeline` JSON for high-fidelity data analysis.
- **Frontend Modularization (FE-MODULAR-S1 - Complete)**:
    - Decomposed monolithic `App.jsx` (954 -> 115 lines) and `App.css` (1061 -> 520 lines) into modular architecture.
    - Plan: [.milestone/frontend_modularization.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/frontend_modularization.md)
- **Sync and Merge Hardening (SYNC-HARDEN-S1 - Phase A)**:
    - Resolving the "Refresh Gap" by unifying Late-Joiner Sync with the live merger.
    - Implementing Cluster-Aware Timeouts to synchronize expiration for unified groups.
    - Plan: [.open_work/sync_merge_hardening.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/sync_merge_hardening.md)
- **Backend Vectorization Completion (NUMPY-HPOWER-S2 - Implementation)**:
    - Fully vectorizing clustering via `scipy.sparse.csgraph.connected_components`.
    - Implementing integer-based bitmasking for O(1) subset detection.
    - Eliminating remaining Python loops in `engine.py` and `cluster_utils.py`.
    - Plan: [.open_work/backend_vectorization_completion.md](file:///c:/Users/amirl/.gemini/antigravity/brain/79a8286c-22a6-44e5-b721-4024971c6106/implementation_plan.md)
    - `context/TacticalContext.jsx`: Global state provider with WebSocket lifecycle, audio engine, all actions/derived state.
    - `utils/constants.js`: Centralized env detection, WS URLs, geodata derivations, color tokens, Leaflet icon fix.
    - `components/Map/MapViewer.jsx`: Isolated Leaflet container with base layer and coordinate sync.
    - `components/Map/ThreatOverlay.jsx`: Per-event rendering of clusters, trajectories, origin highlights, TrackingDrone.
    - `components/Sidebar/Sidebar.jsx`: Modular drawer with Live/History/Sandbox panels and mobile drag behavior.
    - `styles/layout.css`: Structural layout rules (grid, flex, mobile breakpoints).
    - `styles/animations.css`: All @keyframes and animation-applying utility classes.
    - Plan: [.open_work/frontend_modularization.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/frontend_modularization.md)
