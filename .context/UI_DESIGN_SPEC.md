# IRON SIGHT: TACTICAL UI DESIGN SPECIFICATION (TDS)

This document defines the mandatory UI design standards and color palettes for the Iron Sight tactical dashboard. Any interface modification must adhere to these aesthetics to maintain "military-grade" visual fidelity.

---

## 1. DESIGN PRINCIPLES
*   **High Contrast**: Dark backgrounds with vibrant tactical overlays.
*   **Status-Driven**: Red for Live/Threat, Blue for Sandbox/Archive.
*   **Glassmorphism**: Use of background blur and transparency for premium depth.
*   **Motion**: Disciplined 5s animations (5 cycles max) to minimize GPU overhead.

---

## 2. COLOR PALETTE (CSS TOKENS)

| Token | Hex/RGBA | Usage |
| :--- | :--- | :--- |
| **`--bg-primary`** | `#0a0a0c` | Main application background. |
| **`--tactical-red`** | `#ff4d4d` | Live threat indicators, primary accent. |
| **`--tactical-blue`** | `#4d94ff` | History & Sandbox indicators. |
| **`--highlight-red`** | `#ff0000` | Critical threat highlighting, alerts. |
| **`--highlight-blue`** | `#0066ff` | Sandbox highlight, data selection. |
| **`--success`** | `#3ef0a2` | Online status, successful intercept. |
| **`--text-main`** | `#e0e0e0` | Primary readable text. |
| **`--text-sub`** | `#888` | Metadata, labels, secondary information. |

---

## 3. UI MODULES & ARCHITECTURE

### **A. SPLASH SCREEN (Boot Sequence)**
*   **Radar Scanner**: Conic-gradient "sweep" animation (2s linear).
*   **Logo Glow**: Pulse animation on `/favicon.png`.
*   **Terminal Lines**: JetBrains Mono log stream (Uplink, Geodata, Trajectory Engine).

### **B. TACTICAL HEADER**
*   **Status Pill**: Dynamic status indicator (`online`, `degraded`, `offline`).
*   **Uplink Identity**: Explicitly labels the current telemetry source (e.g., `LIVE INTERCEPT: Scout-HL`).
*   **Mute Toggle**: Global audio control for tactical alerts.

### **C. INTELLIGENCE MAP (Leaflet Engine)**
*   **Polygon Boundaries**: Dynamic coloring based on origin (Threat vs Base).
*   **Trajectory Vectoring**: Dashed lines connecting Origin Pins to Target Centroids.
*   **Origin Pin**: DivIcon containing the origin label and threat glow.

### **D. COMMAND SIDEBAR**
*   **Live Intercept**: Total clusters, target count, and real-time alert feed.
*   **Mission Archive**: Historical rewind list with date/time metadata.
*   **Tactical Sandbox**: Multi-region city picker for hypothetical threat analysis.

### **E. MOBILE BOTTOM SHEET (≤1024px) — MANDATORY**

Full contract: [MOBILE_SHELL_SPEC.md](./MOBILE_SHELL_SPEC.md). Summary:

| State | What user sees |
|--------|----------------|
| **Collapsed** | Drag pill strip only (no tab labels). Pull up to expand. |
| **Expanded** | Tabs (LIVE / HISTORY / SANDBOX) + panel content. |

*   **Peek measurement:** `.sidebar-drag-zone` height only (not tabs).
*   **Collapse offset:** measured `sidebarHeight - peekHeight`, not viewport × 0.78.
*   **Drag:** `useMotionValue(y)` — never `animate={{ y }}` on the draggable aside.
*   **Tab tap:** switches panel only; does not force-expand the sheet.
*   **Handle:** ~40px pill (`::after`), safe-area on drag zone; sheet flush to viewport bottom (`position: fixed`).

### **F. MOBILE HEADER (≤1024px)**

*   **Bar:** single 45px row — logo + status (sizes unchanged from mobile tokens).
*   **Clock:** absolute below bar, over map — **not** a second row inside the bar.
*   **Desktop (≥1025px):** clock centered between logo and mute/status in one row.

---

## 4. TYPOGRAPHY
*   **Primary Font**: `Outfit` (Modern, clean, high-readability).
*   **Technical Mono**: `JetBrains Mono` (Terminal outputs, metadata, IDs).

---

## 5. UI DYNAMICS
*   **Pulse Animation**: 1s duration, 5 cycles, `forwards` fill termination.
*   **Map Fly-to**: `0.6s` `flyTo`, `0.8s` `fitBounds` (see `MapViewer.jsx`). Skip when bounds unchanged.
*   **Splash exit:** opacity fade ~0.45s only (no scale).
*   **Boot:** map/header/sidebar mount after `isReady` (see MOBILE_SHELL_SPEC).
