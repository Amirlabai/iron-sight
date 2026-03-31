# IRON SIGHT: STRATEGIC COMMUNICATION PROTOCOL (SCP)

This document defines the mandatory communication standards between the tactical components of the Iron Sight system. Any deviation from these "words" will result in intelligence failure.

---

## 1. TACTICAL UPLINK (Backend <-> Relay Bridge)
Connecting the Render Backend to the Israel-based Relay Bridge.

*   **Endpoint**: `GET /alerts`
*   **Mandatory Header**: `x-relay-auth` (Handshake Key)
*   **Payload Format (JSON)**:
    *   `id`: String (Unique Alert Identifier)
    *   `data`: Array (List of hit cities/areas)
    *   `cat`: String/Int (Category: 1=Rockets, 10=Event Ended)
    *   `title`: String (Descriptive tactical title)

> [!IMPORTANT]
> The Backend is **Dual-Compatible**, supporting both raw fields (`data`) and wrapper fields (`cities`) if the relay library version changes.

---

## 2. REAL-TIME DOWNLINK (Frontend <-> Backend)
Distributing strategic intelligence to the dashboard via WebSockets.

*   **Endpoint**: `WS /ws`
*   **Message Types**:
    *   `health_status`: Connection health and relay availability.
    *   `alert`: Unified strategic threat analysis.
*   **Alert Object**:
    *   `id`: Current active ID.
    *   `all_cities`: Array of mapping objects (Name + Lat/Lon).
    *   `trajectories`: Array of calculated flight paths.
    *   `is_drill`: Boolean (Safety check).

---

## 3. CALIBRATION API (Human-in-the-Loop)
Allowing manual override of theater attribution.

*   **Endpoint**: `POST /api/calibrate`
*   **Mandatory Header**: `X-Mission-Key` (Authorization)
*   **Payload**: `{ "id": "alert_id", "origin": "Correct_Theater" }`

---

## 4. VERSIONING & METADATA
Ensuring all components are on the same sprint.

*   **Endpoint**: `GET /status` (on Backend)
*   **Structure**: `{ "version": "X.Y.Z", "status": "Alpha" }`
