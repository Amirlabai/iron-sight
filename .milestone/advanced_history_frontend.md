# Advanced History: Frontend Visualization (MISSION: HISTORY-ADV-FRONTEND)

This mission upgrades the tactical history display with real-time category filtering, premium expandable motion cards, and high-fidelity regional city segregation via `lamas_data.json` area mapping.

## Proposed Changes

### Dashboard Context Layer

#### [MODIFY] [TacticalContext.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/context/TacticalContext.jsx)
- **State Integration**: Add `historyFilter` (default: 'all') and provide `setHistoryFilter` via context.
- **Dynamic Fetcher**: Implement `fetchHistory(category)` to request filtered streams from the REST API.
- **Reactivity**: Update the initial sync and lifecycle hooks to respect the active filter.

### Dashboard UI Layer

#### [MODIFY] [Sidebar.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/components/Sidebar/Sidebar.jsx)
- **Advanced Filter Bar**: Implement a high-fidelity category selector (All, Missiles, Drones, Earthquakes) at the top of the history list.
- **Expandable History Components**: Refactor history items as `motion.div` cards that expand on click to reveal regional details.
- **Regional Segregation Engine**:
    - Implement the "Area Mapper" to cluster cities under Hebrew area headers (e.g. "ישראל", "מחוז אילת") using existing `regionalData`.
- **Aesthetics**: Integrated Lucide icons for each category (`Rocket`, `Plane`, `Activity`, `ShieldAlert`) and layout animations via `AnimatePresence`.

### Dashboard Styles Layer

#### [MODIFY] [App.css](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.css)
- **Glassmorphic Cards**: styling for expanded history states with category-coded border-glows.
- **Filter Tab UI**: Minimalist, animated tab bar with active state persistence.
- **Area Grouping Styles**: Hierarchy rules for regional headers and city pills within expanded views.

## Verification Plan

### Automated Tests
- **Mapper Parity**: Run unit test script to verify city-to-area mapping against `lamas_data.json`.
- **Filter Reactivity**: Confirm Sidebar list updates immediately upon tab click via `console.log` audit.

### Manual Verification
- **Visual Audit**:
    - Expand a massive salvo history item; verify that Target lists are structured under Area headers.
    - Toggle the "DRONES" filter and verify only Hostile Aircraft alerts remain.
    - Verify smooth "spring" animations when expanding cards and switching tabs.

---

## Implementation Record

Completed: 2026-04-06

### Changes Deployed

| File | Change |
|---|---|
| `TacticalContext.jsx` | Added `historyFilter` state and `fetchHistory` dynamic retrieval. |
| `Sidebar.jsx` | Implemented filter tabs, expandable cards, and regional area grouping. |
| `App.css` | Added Glassmorphic styling for cards and animated filter bar UI. |

### Summary

Successfully upgraded the tactical history interface with a category-aware unified stream. History items are now interactive, expanding to reveal cities grouped by their geographical area (e.g., מחוז צפון) for better intelligence analysis. The implementation uses Framer Motion for smooth layout transitions and Lucide for category iconography.
