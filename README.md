# IRON SIGHT | Real-Time Rocket Tracking Dashboard

An advanced, standalone rocket alert clustering and trajectory tracking system for Israel.

## Features
- **Real-Time Clustering**: Automatically groups alerts within a 10km radius.
- **Trajectory Retracing**: Estimates launch origins (Gaza, Lebanon, Yemen, Iran) based on geographic heuristics.
- **Minimalist Dark UI**: Premium, high-contrast dashboard with smooth animations.
- **WebSocket Synchronization**: Sub-second data streaming from the backend.

---

## Setup & Startup Guide

### 1. Backend (Python)
The backend polls the Pikud HaOref API and processes telemetry.

**Prerequisites**: Python 3.9+
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the backend:
   ```bash
   python main.py
   ```
   *The server will start on port 8080 by default.*

### 2. Dashboard (Frontend - React)
The frontend provides the interactive map and alert visualization.

**Prerequisites**: Node.js 18+
1. Navigate to the `dashboard` directory:
   ```bash
   cd dashboard
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dashboard:
   ```bash
   npm run dev
   ```
   *The dashboard will be available at http://localhost:5173.*

---

## Technical Details
- **Clustering**: 10km threshold (~0.09 degrees).
- **Update Frequency**: 3-second polling interval (optimized for real-time responsiveness).
- **Stack**: Python (Aiohttp), React (Vite, Leaflet, Framer Motion).

Designed for Boss Man.
