#include <.open_work/>
#include <.milestone/>

# IRON SIGHT MISSION STATUS

- [x] MISSION: Israel-Based Alert Relay (Node.js)
- [x] MISSION: Multi-Source Relay Bridge (403 Bypass)
- **High-Resolution Geodata Suite**: 360° high-fidelity silhouettes for Gaza, Lebanon, Israel, Iran, North Iran, and Yemen.
- **Dynamic Strategic Depth**: Calibrated strike projections (Gaza 0.5°, Lebanon 1.0°, North Iran 16.0°, Iran 18.0°, Yemen 20.0°).
- **GPU Optimized Suite**: Zero-Cost Halo system & Disciplined Pulse (5 cycles).
- **Theater Discrimination**: Real-time `is_point_in_polygon` detection for the Iranian northern sector.
- **Strategic Highlight Alias**: Automated regional mapping (`North Iran` -> `Iran`) for visual continuity.

# Iron Sight: Project Status
Updated: 2026-04-09 16:34

## Current Phase: Optimization & Hardening
Status: **ACTIVE** - Resolving visual trajectory redundancy.

### Recent Accomplishments
- [x] Consolidated multi-origin trajectories in `merge_event_group`.
- [x] Standardized origin naming (stripping whitespace) in `TrackingEngine`.
- [x] Unified trajectory projection for collective cluster fronts (Lebanon/Iran).
- [x] Refactored `ThreatProcessor` for missile trajectory consistency.
- [x] **Mission Archive Persistence**: Migrated from `history.json` to **MongoDB Atlas**.
- [x] **Secret Intelligence Suite**: Implemented `.env` for tactical credential management.
- [x] **Strategic Calculation Borders**: Decoupled detection polygons from visual silhouettes for robust origin vectoring.
- [x] **Tactical Origin Validation**: Automatic fallback to fixed coordinates for unreliable projections.
- [x] **Asynchronous DB Engine**: Integrated `motor` for non-blocking history synchronization.
- [x] **Historical Data Patch**: Successfully re-evaluated legacy salvos via `fix_history.py`.
- [x] **Dashboard Visual & Mobile Restoration**:
    - Restored origin high-fidelity boundary polygons in `ThreatOverlay.jsx` for all trajectories.
    - Hardened history regional grouping in `Sidebar.jsx` and data fetching in `TacticalContext.jsx` to prevent blackout crashes.
    - Calibrated `DEFAULT_ZOOM` for mobile responsiveness.
- [x] **Dashboard UI Optimization**:
    - Stripped 'layout' prop from history cards to eliminate "jumping" and reduce memory overhead.
    - Fixed history expansion "ghosting" by transitioning to unique `event.id` React keys.
    - Implemented automatic expansion state reset when alternating between history filters.
    - Conditionally hidden summary regional breakdown in history cards when expanded to reduce visual clutter.
    - Optimized history filter layout with `flex-wrap` to support multi-row button display on smaller screens.
- [x] **Smart Tactical Zoom (Priority Zooming)**:
    - Implemented `calculateBestMapConfig` in `TacticalProvider.jsx` to prioritize furthest origins.
    - Enabled automatic "snap-back" to tighter zoom levels when strategic threats terminate.
    - Synchronized "Return to Live" functionality with multi-threat awareness.
- [x] **Tactical Sandbox Suite**: Automated dry-run engine for cluster analysis and trajectory previews.
- [x] **Strategic Analysis CLI**: Independent utility for command-line theater discrimination testing.
- [x] **Networking Stabilization**: Absolute `TACTICAL_API_URL` logic for Vercel-to-Render communication.
- [x] **Asset Pathing Resilience**: Fixed `lamas_data.json` loading via absolute `os.path.dirname(__file__)` logic.
- [x] **Pathing Resilience**: Fixed backend asset localization for cross-environment execution.
- [x] **Runtime Audit**: Verified deployment stability against Render's Python 3.14 rollout; version locked at 3.12.0 via `.python-version`.
- [x] **Monorepo Pathing**: Explicitly set `rootDir: backend` in `render.yaml` and fixed start command with `python` prefix.
- [x] **GitHub Actions Stabilization**: Patched `version-sync.yml` with `contents: write` permissions to allow automated version bumps.
- [x] MISSION: UI Design Specification (TDS)
- [x] MISSION: Tactical Mobile Optimization (Drawer & Header Scaling)
- [x] MISSION: Mobile Tab Calibration (70% Expansion)
- [x] MISSION: Pulse Normalization (Absolute Circularity)
- [x] **Strategic Border Utility Suite**: Implemented `border_utils.py` for high-fidelity conversion between TXT and JSON geodata.
- [x] **Reversed Tactical Geodata**: Generated reversed-coordinate `.txt` archives for `calculation_borders` and `tactical_borders`.
- [x] MISSION: Tactical Relay Filtering (type: newsFlash Logic)
- [x] MISSION: WebSocket Active Salvo Persistence (Late-Joiner Synchronization)
- [x] **MISSION**: Cluster-Based Iran Filtering (Dual-Tier Threshold 10/40)
- [x] **MISSION**: Tactical Reset Hardening (Immediate News Flash Response)
- [x] **MISSION**: Numpy Vectorized Strategy Engine (Backend Hardware Acceleration)
- [x] **MISSION**: Professional Backend Modular Refactor (`src/` architecture)
- [x] **MISSION**: Multi-Threat Tactical Expansion (`earthQuake`, `hostileAircraft`, `terroristInfiltration`)
- [x] **MISSION**: Independent Tactical Persistence (Multi-Collection Storage)
- [x] **MISSION**: Geographic Multi-Threat Visual Orchestration (React Tracker)
- [x] **MISSION**: ID-Driven Multi-Threat Architecture (Simultaneous Alert Lifecycle)
- [x] **MISSION**: Lifecycle Hardening (Inactivity Timeout + Mandatory Detection Logging)
- [x] **MISSION**: Event Lifecycle Logging (MongoDB Stabilization)
- [x] **MISSION**: Socket Synchronization Review (Late-Joiner Protocol)
- [x] **MISSION**: Tactical Intelligence & Visual Hardening
- [x] **MISSION**: Tactical Merging and Visual Restoration (Hardening)
- [x] **MISSION**: Tactical Visual Refinement
- [x] **MISSION**: Tactical Audio Engine
- [x] **MISSION**: Automated Log Export to CSV
- [x] **MISSION**: Frontend Modularization (Alpha)
- [x] **MISSION**: Sync and Merge Hardening (Alpha)
- [x] **MISSION**: Backend Vectorization (Numpy/SciPy Optimization)
- [x] **MISSION**: Advanced History: Backend Aggregation
- [x] **MISSION**: Advanced History: Frontend Visualization
- [x] **MISSION**: Tactical History Merging
- [x] **MISSION**: Tactical Health Stabilization (Undefined Fix)
- [x] **MISSION**: History Fixer Restoration (Highlighting & Mobile Optimization)
- [x] **MISSION**: Dashboard Visual & Mobile Hardening (Restoration)
- [x] **MISSION**: History Aircraft Card Crash Fix (Hardening)
- [x] **MISSION**: History Tactical Recalculation (Data Integrity)
- [x] **MISSION**: Smart Tactical Zoom (Multi-Threat Priority Zooming)
- [x] **MISSION**: Dashboard UI Optimization (Memory & State Hardening)
- [x] **MISSION**: Simplified Tactical Map (Label-Free Dark Mode integration)
- [x] **MISSION**: Tactical History Merging (Shared-City Logic)
- [x] **DATA_CORRECTION**: Lebanon Salvo `134200308790000000`
- [x] **MISSION**: Tactical newsFlash Recalibration (Silent Ghost + Superseding)
- [x] **MISSION**: Historical Trajectory Hardening (INDEX_ERROR_HARDENING) - [.milestone/index_error_hardening.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/index_error_hardening.md)
- [x] **MISSION**: Tactical Cluster Shape Inflation (CLUSTER_INFLATION) - [.milestone/cluster_inflation.md](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/.milestone/cluster_inflation.md)




---
**Mission Status**: **HARDENED** | CONSOLE ANONYMIZED
- Transitioned to ID-Driven Architecture: `active_events{}` dictionary with `last_update_time`-based inactivity timeout (5 min silence).
- **Shared-City Merging**: Upgraded clustering from subset/superset to intersection-based. Multi-regional merges (e.g. Center/North) now require 50% intersection; same-region or Gaza alerts merge with 1 shared city.
- **Unified Re-computation**: Merged events now strip accumulated trajectories and re-run ballistic analysis on the full city set for a single 'Master' trajectory.
- **Multi-Hull Persistence**: Restored `engine.cluster` support allowing a single alert ID to maintain multiple distinct tactical polygons (e.g. simultaneous North and South hits).
- **Superseding Logic**: Implemented real-time protocol where actual `missiles` alerts immediately terminate overlapping `newsFlash` ghosts.
- **Silent Ghost**: `newsFlash` alerts maintain ghostly visuals but trigger zero audio to denote their "Potential" status.
- **Auditor Multi-Select**: History Fixer now supports manual batch merging of fragmented historical records.
- **Multi-Alert Broadcast**: Backend pushes `multi_alert` payloads; dashboard renders all threats simultaneously on the map.
- **Networking**: Masked backend infrastructure via Vercel `/api` proxy. Sanitized production logs.
