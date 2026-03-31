/**
 * Iron Sight: Tactical Alert Relay
 * -------------------------------
 * This service acts as a high-fidelity bridge between the Home Front Command (Israel)
 * and the Iron Sight Tactical Engine. It must be deployed on an Israeli IP (VPS/Proxy).
 * 
 * Version: 1.0.0
 * Library: pikud-haoref-api
 */

const http = require('http');
const oref = require('pikud-haoref-api');

// --- Configuration ---
const PORT = process.env.PORT || 3001;
const AUTH_KEY = process.env.RELAY_AUTH_KEY || 'IStac8F12B9A3C4D5E2F17B096D8E';

const server = http.createServer((req, res) => {
    // 1. Authentication Check
    const providedKey = req.headers['x-relay-auth'];
    
    if (providedKey !== AUTH_KEY) {
        console.warn(`[RELAY] Unauthorized access attempt from ${req.socket.remoteAddress}`);
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Unauthorized: Invalid Tactical Key' }));
        return;
    }

    // 2. Routing
    const url = new URL(req.url, `http://${req.headers.host}`);

    // --- GET /alerts ---
    if (url.pathname === '/alerts' && req.method === 'GET') {
        const options = {}; // You can add city filters here if needed
        
        oref.getActiveAlerts((err, alerts) => {
            if (err) {
                console.error(`[RELAY_ERROR] ${new Date().toISOString()} - UPSTREAM_FAIL: ${err.message}`);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Failed to fetch upstream alerts', detail: err.message }));
                return;
            }

            if (alerts.length > 0) {
                console.log(`[RELAY_ALERT] ${new Date().toISOString()} - Detected ${alerts.length} active threats.`);
            } else {
                process.stdout.write('.'); // Heartbeat indicator
            }
            
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(alerts));
        }, options);
    } 
    
    // --- GET /health ---
    else if (url.pathname === '/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'OK', version: '1.0.0', origin: 'Israel' }));
    }

    // --- 404 Not Found ---
    else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Tactical Endpoint Not Found' }));
    }
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`--------------------------------------------------`);
    console.log(` IRON SIGHT RELAY - ACTIVE (Port: ${PORT})`);
    console.log(` AUTH_KEY: ${AUTH_KEY.substring(0, 5)}... (Locked)`);
    console.log(`--------------------------------------------------`);
});
