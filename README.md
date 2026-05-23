# IRON SIGHT | Tactical Airspace Defense Dashboard

![IRON SIGHT](dashboard/public/favicon.png)

**Iron Sight** is an advanced, high-fidelity tactical monitoring system designed for real-time tracking, clustering, and analysis of aerial threats over Israel. It provides a strategic common operating picture (COP) by integrating live data feeds with historical intelligence.

---

## 🚀 Mission Objectives

- **Live Intercept**: Sub-second synchronization of rocket, drone, and infiltration alerts via high-speed WebSockets.
- **Strategic Clustering**: Automated grouping of localized threats into tactical clusters to reduce map clutter and improve situational awareness.
- **Smart Tactical Merging**: Proximity-aware (12km) convex hull generation for historical analysis, unifying separate alert waves into unified strategic zones.
- **Trajectory Vectoring**: Heuristic-based estimation of launch origins (Lebanon, Gaza, Iran, Yemen) with high-fidelity origin highlights and pins.
- **Historical Intelligence**: Deep archive access via MongoDB, supporting time-frame filtering (1h, 12h, 24h) and custom date ranges.
- **Tactical Sandbox**: A "dry-run" environment for hypothesizing threat vectors and analyzing potential impact zones.
- **Mobile-First Hardening**: A condensed, high-density tactical interface optimized for physical mobile hardware and rapid interaction.

---

## 🛠️ Architecture & Stack

### Frontend (Dashboard)
- **Engine**: React 19 + Vite 6
- **Spatial Data**: Leaflet.js with custom Tactical Overlay components.
- **Animations**: Framer Motion with high-stiffness spring physics for a "snappy" tactical feel.
- **State Management**: React Context with a central `TacticalProvider` governing live/archive sync.
- **Geo-Engine**: Custom frontend implementation of the Monotone Chain Convex Hull algorithm for real-time polygon merging.

### Backend (Intelligence Engine)
- **Engine**: Python 3.12 (Asynchronous/Aiohttp)
- **Database**: MongoDB Atlas for persistent mission archiving and historical queries.
- **Telemetry**: Real-time polling of upstream alert APIs with automated clustering and origin detection.
- **WebSocket Gateway**: High-frequency broadcast of mission updates and multi-alert payloads.

---

## ⚙️ Deployment Guide

### Prerequisites
- Python 3.12+
- Node.js 18+
- MongoDB Atlas Connection String

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Configure .env with MONGO_URI and RELAY_URL
python main.py
```

### 2. Frontend Setup
```bash
cd dashboard
npm install
npm run dev
```
*The dashboard will be available at http://localhost:5173.*

**Production URL:** [Live Israel alert map — Iron Sight](https://iron-sight-drab.vercel.app/)

Optional env in `dashboard/.env` (see `dashboard/.env.example`):

- `VITE_SITE_URL` — canonical base for SEO, Open Graph, and sitemap (default: `https://iron-sight-drab.vercel.app`)

---

## 🛰️ System Parameters
- **Live Sync Frequency**: 3.0s polling / Instant WS push.
- **Tactical Clustering Radius**: 10km (Live) / 12km Smart Merge (History).
- **Timezone**: Locked to Jerusalem Standard Time (GMT+3).
- **Security**: Environment-locked relay authentication.

---
**Mission Status**: **HARDENED** | **VERSION 1.0.0-TACTICAL**
*Designed for Boss Man.*
