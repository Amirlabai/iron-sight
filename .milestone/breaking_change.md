# Support Simultaneous Multi-Threat Alerts (ID-Driven Architecture)

Based on the strategic directives, the Iron Sight engine will pivot strictly to an ID-driven lifecycle. This means alerts will be treated as distinct events from creation to termination based solely on their ID, replacing the legacy rolling mathematical clustering completely. 

## Proposed Changes

### 1. Tactical Simulator (`backend/simulator`)

#### [MODIFY] [index.html](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/simulator/index.html)
- **Top-Left Hovering Icons**: Add an active-alert UI layer overlaying the map. Whenever an alert is dispatched, an icon (representing the threat type) with an "X" will appear in the top-left area. 
- **Bottom Bar**: Refactor the control panel into a bottom bar to launch attacks, keeping the screen less crowded.
- **Cancellation**: Clicking the "X" of a hovering icon will trigger a `/end` request specifically aimed at that alert's ID, removing the icon from the UI.

#### [MODIFY] [server.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/simulator/server.py)
- Refactor to act as a strict message queue rather than holding standing state. 
- `/dispatch` will push the threat payload into an outbound queue.
- `/end` will accept a specific `id` and push a `newsFlash` / "האירוע הסתיים" payload tagged with that **exact** `id` into the queue.
- `/relay` will pop and return all payloads in the queue for pickup by the backend, perfectly mirroring real-world Pikud HaOref behavior.

### 2. Backend Command Center (`backend/src`)

#### [MODIFY] [main.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/main.py)
- Replace scalar trackers (`last_alert_id`, `active_salvo`) with a dictionary: `active_events = {}` (keyed by `alert_id`).
- When parsing payloads:
  - **Start Threat**: Add new threats directly into `active_events[alert_id]`.
  - **End Threat**: When a `newsFlash` or "האירוע הסתיים" payload arrives with a specific `id`, map it to `active_events`. Save that specific alert to MongoDB history, remove it from `active_events`, and broadcast the update.
- **Broadcaster**: Continuously push `{"type": "multi_alert", "events": [...]}` containing only currently active threats.

#### [MODIFY] [threat_processor.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/core/threat_processor.py)
- **"No More Math Clustering"**: Strip out ALL mathematical/DBSCAN clustering logic (`self.engine.cluster()`).
- All `cities` inside a single payload (tied to one `id`) will be treated as **one unified cluster**. 
- Calculate one single hull, and one single centroid for the entire ID's target list.
- Calculate the launch origin and trajectory targeting that specific ID's centroid.
- Apply this logic uniformly to `_process_missiles`, dropping the complex origin-splitting logic.

#### [MODIFY] [ws_manager.py](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/backend/src/api/ws_manager.py)
- Replace single-threat syncing. New clients will receive the entire `active_events` dictionary upon connecting.

### 3. Intelligence Dashboard (`dashboard/src`)

#### [MODIFY] [App.jsx](file:///c:/Users/amirl/OneDrive/Documents/GitHub/iron-sight/dashboard/src/App.jsx)
- **State Switch:** Replace `liveEvent` with `const [liveEvents, setLiveEvents] = useState([])`.
- **WebSocket Handlers:** Update the handler to process `type === 'multi_alert'`, populating the `liveEvents` array and purging cancelled IDs immediately.
- **Map Dynamic Renderer:** 
  - Loop over `liveEvents` to render multiple threats (whether rockets, drones, or infiltrations) simultaneously.
  - Distinguish overlapping threats through distinct rendering logic (so a drone sweep and a rocket salvo don't break Leaflet's layers).
- **Sidebar Tabs:** Update the LIVE tab to iterate over and display stats for all active IDs seamlessly.

## User Review Required

Does this updated architecture perfectly align with the ID-driven approach you outlined? Once approved, I will begin execution without hesitation.
