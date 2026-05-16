# IRON SIGHT | Tactical Backend Engine

The **Iron Sight Backend** is a high-availability intelligence engine responsible for alert ingestion, spatial clustering, and historical mission archiving.

## 🛰️ Core Capabilities

- **Real-Time Ingestion**: Polls upstream telemetry APIs every 3 seconds for mission-critical alerts.
- **Spatial Intelligence**:
    - **Live Clustering**: Groups alerts within a 10km radius using a point-in-polygon (PIP) engine.
    - **Origin Detection**: Automatically vectors incoming threats back to their likely launch origins (Lebanon, Iran, Yemen, etc.) using `calculation_borders.json`.
- **Mission Archiving**: Full persistence of every alert wave into **MongoDB Atlas** for long-term strategic analysis.
- **Unified API & WebSocket Gateway**:
    - `GET /api/history`: High-speed historical queries with category and time-window support.
    - `WS /ws`: Sub-second broadcasting of tactical updates to connected dashboards.
- **Data Utilities**:
    - `migrate_history.py`: Tool for ingesting legacy JSON datasets into the cloud database.
    - `border_utils.py`: High-fidelity synchronization between coordinate archives and tactical JSON maps.

## 🛠️ Technical Stack

- **Runtime**: Python 3.12 (Asynchronous)
- **Framework**: Aiohttp (Server & WebSockets)
- **Database**: MongoDB (Motor async driver)
- **Validation**: Strict schema enforcement for tactical payloads.

## 🚀 Getting Started

1. **Environment Setup**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configuration**:
   Ensure `.env` contains:
   ```env
   MONGO_URI=mongodb+srv://...
   RELAY_URL=...
   RELAY_AUTH_KEY=...
   ```
3. **Run Engine**:
   ```bash
   python main.py
   ```

---
**Mission Status**: **STABLE** | **ALPHA v0.6.0**
