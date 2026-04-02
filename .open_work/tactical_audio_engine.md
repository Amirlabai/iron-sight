# Tactical Audio Engine (MISSION: AUDIO_DEPLOY)

Implement a robust, deduplicated alert audio engine to synchronize with live tactical events.

## Proposed Changes

### Strategic Dashboard
#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- **Asset Imports**: Import `missile_alert.mp3` and `hostileAircraftIntrusion_alert.mp3` from `assets/sounds/`.
- **Identity Tracking**: Implement a `useRef` based identity set to track "Announced" alert IDs.
- **Playback Orchestration**:
    - For each `liveEvent` update, compare against the announced set.
    - **missiles**: Trigger single-cycle playback.
    - **hostileAircraftIntrusion / drones**: Trigger double-cycle playback (sequenced via the `onended` event).
- **Cleanup**: Ensure all `Audio` objects are properly cleared during event purging to prevent memory leaks.

## Verification Plan

### Automated Tests
- **Playback Audit**: Simulate 5 rapid coordinate updates to a single alert ID and verify through console logs (or audio driver status) that only ONE playback cycle was initiated.
- **Loop Validation**: Confirm that `hostileAircraftIntrusion` triggers exactly 2 audio completion events.

### Manual Verification
- Visual+Audio check: Dispatch the "Rishon" and "Holon" simulator missions and listen for the high-priority missile ping (1x).
- Dispatch a "Drone" mission and confirm the authoritative double-loop alert.
