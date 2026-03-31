# IRON SIGHT: TACTICAL BACKEND ENGINE (v0.5.x)

This directory contains the central intelligence engine for the **Iron Sight** tactical dashboard. It is responsible for real-time alert processing, cluster analysis, trajectory vectoring, and strategic mapping.

## Core Components

- **`main.py`**: The primary execution entry point. 
    - Hosts a high-performance **Aiohttp** server with WebSocket support.
    - Manages the **Real-Time Monitoring Loop** for upstream alert detection.
    - Interfaces with **MongoDB Atlas** for long-term mission archive persistence.
    - Implements **Strategic Calibration** endpoints for human-in-the-loop trajectory overrides.

- **`border_utils.py`**: Strategic Geodata Utility.
    - High-fidelity conversion between `.txt` coordinate archives and `.json` boundary payloads.
    - Supports automated **Coordinate Reversal** (lat/lon swapping) for cross-platform compatibility.

- **`migrate_history.py`**: Intelligence Data Migration.
    - Utility script to migrate legacy `history.json` files to the MongoDB Atlas cluster.

- **`mine_tactical_vectors.py`**: Cluster Analysis Suite.
    - Investigative tool for analyzing historical salvos and mining tactical trajectory vectors.

## Strategic Geodata Management

The engine uses a dual-tier boundary system:
1.  **`tactical_borders.json`**: Detailed 360° high-fidelity silhouettes for visual rendering on the dashboard.
2.  **`calculation_borders.json`**: Simplified, drift-resistant polygons used by the `TrackingEngine` for point-in-polygon (PIP) origin detection.

### Geodata Utility Commands

Use the `border_utils.py` tool for geodata synchronization:

#### 1. Convert TXT to JSON (JSON Generation)
Reads a formatted `.txt` file and generates a compatible `.json` boundary map.
```bash
python backend/border_utils.py t2j <input_file.txt> <output_file.json>
```

#### 2. Convert JSON to TXT (Archive with Reversed Order)
Extracts coordinates from a `.json` file and saves them to a `.txt` archive with **swapped [longitude, latitude] coordinates**.
```bash
python backend/border_utils.py j2t <input_file.json> <output_file.txt> --reverse
```

## Deployment & Development

### Local Execution
1. Ensure the virtual environment is active.
2. Configure `.env` with `MONGO_URI`, `RELAY_URL`, and `RELAY_AUTH_KEY`.
3. Run the engine:
   ```bash
   python backend/main.py
   ```

### Requirements
- **Python**: 3.12+ (Locked at 3.12.0 for production stability).
- **Environment**: Root level `.env` or system environment variables.
- **Dependencies**: `aiohttp`, `motor`, `python-dotenv`, `aiohttp-cors`.

---
**Mission Status**: **STABLE** | **ALPHA v0.5.4**
