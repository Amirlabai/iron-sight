#include <.context/COMMUNICATION_PROTOCOL.md>
#include <.context/UI_DESIGN_SPEC.md>

# IRON SIGHT: TACTICAL CONTEXT

> [!IMPORTANT]
> **SOURCE OF TRUTH DIRECTIVE**: Before modifying ANY communication logic (Headers, Endpoints, JSON payloads), you MUST read the [STRATEGIC COMMUNICATION PROTOCOL (SCP)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md) immediately. For UI changes, color palettes, or component architecture, you MUST read the [UI DESIGN SPECIFICATION (TDS)](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/UI_DESIGN_SPEC.md) first. Failure to adhere to these protocols will result in Strategic De-sync or UI Degradation.

## MISSION OVERVIEW
Iron Sight is a real-time, strategic intelligence engine designed to detect, analyze, and visualize tactical threats in the Israeli theater. 
It converts raw Pikud HaOref API feeds into actionable intelligence through real-time clustering, trajectory vectoring, and strategic mapping.

## STRATEGIC LOGIC (TACTICAL-CORE-v1.2)
- **Automatic Merging**: Regional hard-coded adjacency rules determine consolidation. Same-region alerts merge on 1 shared city; cross-region requires 50% intersection.
- **Trajectory Consolidation**: Enforcement of exactly one representative trajectory per origin group (e.g., Lebanon) during detection and merging.
- **Origin Projection**: Uses regression vectors from cluster city sets to project entry points within tactical boundaries. Recalculated projection points to the specific entry point for the whole group.
- **Depth Calibration**: Standardized strategic depths (Gaza 0.5, Lebanon 0.5, Iran 16.0, Yemen 20.0).

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
Transitioned to Development Alpha.

### RECENT OPERATIONS
- **Uplink Consolidation**: Established the Israeli Relay Bridge as the sole tactical uplink.
- **Protocol Alignment**: Standardized all cross-system communication via the [SCP](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/COMMUNICATION_PROTOCOL.md).
- **Reset Protocol Hardening**: Shortened dashboard reset delay to 10s for explicit "Event Ended" signals, with immediate backend state purging.
- **Cluster-Based Iran Filtering**: Applied a dual-tier threshold system (`MIN_IRAN_THRESHOLD=10`, `MAX_IRAN_THRESHOLD=40`) to map massive salvos explicitly to Iran while demoting sparse clusters to regional origins.
- **Tactical Console Hardening**: 
    - Masked backend infrastructure via Vercel `/api` rewrites, anonymizing REST traffic.
    - Eliminated diagnostic console warnings (`MISSION_SYNC_TIMEOUT`) and sanitized production logs.
    - Integrated `IS_PROD` environment detection for silent telemetry.
- **Backend Modernization**:
    - Migrated to professional `src/` modular architecture.
    - Integrated multi-threat logic for drones, infiltrations, and seismic alerts.
    - Implemented category-aware visual orchestration (`TrackingDrone` JS Interpolation).
    - Established independent MongoDB collection archives for threat separation.
- **ID-Driven Architecture**:
    - Replaced scalar `last_alert_id`/`active_salvo` with `active_events{}` dictionary keyed by alert ID.
    - Simulator refactored to message queue with per-ID dispatch/cancellation and top-left hovering icons.
    - Stripped DBSCAN clustering from `threat_processor.py`. All cities per ID form one unified cluster.
    - Backend broadcasts `multi_alert` payloads; dashboard renders simultaneous threats via `liveEvents[]` array.
    - End signals target specific IDs or broadcast to all active events with 10s grace period.
    - Lifecycle hardening: replaced `start_time` timeout with `last_update_time` inactivity timeout (5 min silence).
    - Mandatory detection logging: DETECTION_SIGNAL, ROLLING_UPDATE, EVENT_TIMEOUT, EVENT_PERSISTED, EVENT_PURGED.
- **Event Lifecycle Logging**:
    - New `event_logs` MongoDB collection via `COLLECTION_LOGS` config constant.
    - `MongoManager.log_event()` upserts lifecycle documents keyed by `event_id` with full timeline arrays.
    - `main.py` instrumented at all five transition points: DETECTED, UPDATED, END_SIGNAL, TIMEOUT, PURGED.
    - Schema tracks `start_time`, `last_update_time`, `end_time`, `termination_reason`, `city_count`, `city_list`, `updates_count`, and chronological `timeline[]`.
- **Socket Synchronization (Audit)**:
    - Reviewing Late-Joiner synchronization logic between `ws_manager.py` (Backend) and `App.jsx` (Frontend).
    - Ensuring immediate state mirroring for users joining during active multi-alert events.
    - Plan: [.open_work/socket_sync_review.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/socket_sync_review.md)
- **Tactical Visual Refinement**: 
    - Unifying vectors for merged groups, transitioning drones to triangle morphology, and implementing organic/rounded hulls.
    - **Silent Ghost Protocol**: `newsFlash` alerts (Potential Threat Warnings) are non-audible visual indicators that maintain ghostly aesthetics unless superseded by a confirmed missile alert.
    - **Superseding Logic**: Backend automatically terminates active `newsFlash` events if a `missiles` alert with overlapping geographic targets is detected.
- **Tactical Audio Engine (Implementation)**:
    - Dedicated audio driver for deduplicated missile alerts (1x) and drone loops (2x).
    - Plan: [.open_work/tactical_audio_engine.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/status.md)
- **Log Export Utility**:
    - Implemented `scripts/export_logs.py` for automated extraction of `event_logs` from MongoDB to CSV.
    - Flattens nested `city_list` and serializes `timeline` JSON for high-fidelity data analysis.

- **Frontend Modularization (FE-MODULAR-S1 - Complete)**:
    - Decomposed monolithic `App.jsx` (954 -> 115 lines) and `App.css` (1061 -> 520 lines) into modular architecture.
    - Plan: [.milestone/frontend_modularization.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/frontend_modularization.md)
- **Sync and Merge Hardening (Alpha - Milestone)**:
    - Resolved Refresh Gap via unified Late-Joiner sync.
    - Implemented Cluster-Aware Timeouts for synchronized expiration.
    - Plan: [.milestone/sync_merge_hardening.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/sync_merge_hardening.md)
- **Backend Vectorization (NUMPY-HPOWER-S1 - Complete)**:
    - Vectorized $O(N^2)$ loops in `cluster_utils.py` and `engine.py` using NumPy/SciPy.
    - Achieved ~12x speedup for massive thread salvos.
    - Plan: [.milestone/backend_vectorization.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/backend_vectorization.md)
- **Advanced History: Backend Aggregation (HISTORY-ADV-BACKEND - Complete)**:
    - Unified missiles, drones, infiltrations, and earthquakes into a single consolidated history stream.
    - Implemented parallel async fetching and interleaved chronological sorting by alert ID.
    - Enhanced REST API with `?category=` filter support for granular dashboard retrieval.
    - Plan: [.milestone/advanced_history_backend.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/advanced_history_backend.md)
- **Advanced History: Frontend Visualization (HISTORY-ADV-FRONTEND)**:
    - Integrated real-time category filtering and regional area grouping in history.
    - Plan: [.milestone/advanced_history_frontend.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/advanced_history_frontend.md)
- [x] **Tactical History Merging**:
    - Unified clustered alerts into single history records to resolve ID-driven fragmentation.
    - Implemented state-independent grouping and consolidated Master Payload persistence.
    - Plan: [.milestone/history_merging.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/history_merging.md)
- [x] **Tactical Health Stabilization**:
    - Fixed "undefined" live intercept status by adding `upstream_source` to backend health signals.
    - Hardened frontend `TacticalContext` with a default 'OPERATIONAL' fallback for status sources.
- [x] **History Fixer Restoration**:
    - Restored origin highlighting via `TACTICAL_BOUNDARIES` and `Polygon` rendering.
    - Fixed aircraft filter "blackout" crash via strict coordinate safety guards.
    - Implemented responsive `DEFAULT_ZOOM` and mobile-optimized layouts for phones.
- [x] **Dashboard UI Optimization**:
    - Stripped 'layout' prop from history cards to eliminate "jumping" and reduce memory overhead.
    - Fixed history expansion "ghosting" by transitioning to unique `event.id` React keys.
    - Implemented automatic expansion state reset when alternating between history filters.
    - Conditionally hidden summary regional breakdown in history cards when expanded to reduce visual clutter.
    - Optimized history filter layout with `flex-wrap` to support multi-row button display on smaller screens.
    - Synchronized history filter active colors with category-specific threat colors (Red/Orange/Purple/Green).
- [x] **Dashboard Visual & Mobile Restoration**:
    - Restored origin high-fidelity boundary polygons in `ThreatOverlay.jsx` for all trajectories.
    - Hardened history regional grouping in `Sidebar.jsx` and data fetching in `TacticalContext.jsx` to prevent blackout crashes.
    - Calibrated `DEFAULT_ZOOM` for mobile responsiveness.
- [x] **Smart Tactical Zoom (Priority Zooming)**:
    - Implemented `calculateBestMapConfig` in `TacticalProvider.jsx` to prioritize furthest origins.
    - Enabled automatic "snap-back" to tighter zoom levels when strategic threats terminate.
    - Synchronized "Return to Live" functionality with multi-threat awareness.
- **Historical Trajectory Hardening (v1.0.3 - Completed)**:
    - Implemented defensive guard clauses for safe trajectory array access and optimized MongoDB verified fetches.
    - Plan: [.milestone/index_error_hardening.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/index_error_hardening.md)
- **Tactical Cluster Shape Inflation (v1.0.4 - Complete)**:
    - implementing configurable hull expansion for drones and missiles in the engine and threat processor layers.
    - Plan: [.open_work/cluster_inflation.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/cluster_inflation.md)
- **Strategic Origin Filtering (v1.0.5 - Complete)**:
    - Gated Iran/Yemen origin detection behind `allow_strategic` flag derived from newsFlash context.
    - `engine.get_origin` skips long-range polygon projection when `allow_strategic=False`.
    - `threat_processor._process_missiles` calculates `allow_strategic` from batch pre-scan and active newsFlash events.
    - `main.py` pre-scans each alert batch for newsFlash presence and passes context through the pipeline.
    - Plan: [.open_work/strategic_origin_filtering.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/strategic_origin_filtering.md)
- **Multi-Origin Tactical Zoom & Centering (v1.0.6 - Complete)**:
    - `threat_processor._process_missiles` injects `zoom_level` from `engine.zoom_levels` and snaps center to Israel `[31.7, 35.2]` when `len(origin_groups) > 1`.
    - `cluster_utils.merge_event_group` mirrors the same multi-origin zoom/center logic during broadcast merges.
    - `TacticalProvider.calculateBestMapConfig` detects unique origins (normalizing `North Iran` -> `Iran`) and returns `ISRAEL_CENTER` with widest zoom when `uniqueOrigins.size > 1`.
    - Plan: [.open_work/multi_origin_zoom.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/multi_origin_zoom.md)




    - `context/TacticalContext.jsx`: Global state provider with WebSocket lifecycle, audio engine.
    - `utils/constants.js`: Centralized env detection, WS URLs, geodata derivations, color tokens, Leaflet icon fix.
    - `components/Map/MapViewer.jsx`: Isolated Leaflet container with base layer and coordinate sync.
    - `components/Map/ThreatOverlay.jsx`: Per-event rendering of clusters, trajectories, origin highlights, TrackingDrone.
    - `components/Sidebar/Sidebar.jsx`: Modular drawer with Live/History/Sandbox panels and mobile drag behavior.
    - `styles/layout.css`: Structural layout rules (grid, flex, mobile breakpoints).
    - `styles/animations.css`: All @keyframes and animation-applying utility classes.
    - Plan: [.open_work/frontend_modularization.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.open_work/frontend_modularization.md)
