import json
import logging
import time
from datetime import datetime
from aiohttp import web
import aiohttp_cors
from src.utils.config import ALLOWED_ORIGINS, WS_PORT, MISSION_KEY, TIMEZONE
from src.utils.cluster_utils import build_merged_payloads
from src.utils.observability import (
    estimate_json_bytes,
    http_observability_middleware,
    log_history_fetch,
    log_ws_session,
)
from src.utils.trajectory_utils import (
    entry_by_origin,
    project_entry_for_origin,
    sync_missile_trajectory_on_verify,
)

logger = logging.getLogger("IronSightBackend")

class WebSocketManager:
    def __init__(self, db_manager, engine, version, push_manager=None):
        self.port = WS_PORT
        self.db = db_manager
        self.engine = engine
        self.version = version
        self.push_manager = push_manager
        self.clients = set()
        self.app = web.Application(middlewares=[http_observability_middleware])
        self.active_events = {}  # Mirrors main.py's active_events for late-joiner sync

        self.cors = aiohttp_cors.setup(self.app, defaults={
            origin: aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            ) for origin in ALLOWED_ORIGINS
        })

        self._setup_routes()

    def _setup_routes(self):
        self.add_route("GET", "/ws", self.ws_handler)
        self.add_route("GET", "/", self.health_handler)
        self.add_route("POST", "/api/calibrate", self.calibrate_handler)
        self.add_route("GET", "/api/history", self.history_handler)
        self.add_route("GET", "/api/history/event", self.history_event_handler)
        self.add_route("GET", "/api/cities", self.cities_handler)
        self.add_route("POST", "/api/history/update", self.update_history_handler)
        self.add_route("POST", "/api/history/split", self.split_history_handler)
        self.add_route("POST", "/api/history/merge", self.merge_history_handler)
        self.add_route("POST", "/api/history/suggest-origin", self.suggest_origin_handler)
        self.add_route("POST", "/api/history/project-entry", self.project_entry_handler)
        self.add_route("POST", "/api/origin/replay", self.origin_replay_handler)
        self.add_route("GET", "/api/history/training-export", self.training_export_handler)
        self.add_route("GET", "/api/push/vapid-public-key", self.push_vapid_handler)
        self.add_route("POST", "/api/push/subscribe", self.push_subscribe_handler)
        self.add_route("PATCH", "/api/push/location", self.push_location_handler)
        self.add_route("DELETE", "/api/push/unsubscribe", self.push_unsubscribe_handler)

    def add_route(self, method, path, handler):
        resource = self.app.router.add_resource(path)
        self.cors.add(resource.add_route(method, handler))

    async def health_handler(self, request):
        return web.json_response({
            "status": "OPERATIONAL",
            "version": self.version,
            "engine": "IRON SIGHT TACTICAL",
            "timestamp": datetime.now(TIMEZONE).isoformat()
        })

    async def push_vapid_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.get_vapid_public_key():
            return web.json_response({"error": "VAPID not configured"}, status=503)
        return web.json_response({"publicKey": pm.get_vapid_public_key()})

    def _push_client_token(self, request, body=None):
        token = request.headers.get("X-Push-Client-Token")
        if not token and body:
            token = body.get("client_token")
        return token

    async def push_subscribe_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.is_configured():
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            ok, err, client_token = await pm.upsert_subscription(body)
            if not ok:
                return web.json_response({"error": err or "Subscribe failed"}, status=400)
            return web.json_response({"status": "subscribed", "client_token": client_token}, status=201)
        except Exception as e:
            logger.error(f"PUSH_SUBSCRIBE_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def push_location_handler(self, request):
        pm = self.push_manager
        if not pm or not pm.is_configured():
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            endpoint = body.get("endpoint")
            loc = body.get("location") or {}
            client_token = self._push_client_token(request, body)
            if not endpoint or loc.get("lat") is None or loc.get("lng") is None:
                return web.json_response({"error": "Missing endpoint or location"}, status=400)
            if not client_token:
                return web.json_response({"error": "Unauthorized"}, status=401)
            result = await pm.update_location(endpoint, loc["lat"], loc["lng"], client_token)
            if result == "unauthorized":
                return web.json_response({"error": "Unauthorized"}, status=401)
            if result == "not_found":
                return web.json_response({"error": "Subscription not found"}, status=404)
            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"PUSH_LOCATION_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def push_unsubscribe_handler(self, request):
        pm = self.push_manager
        if not pm:
            return web.json_response({"error": "Push service unavailable"}, status=503)
        try:
            body = await request.json()
            endpoint = body.get("endpoint")
            client_token = self._push_client_token(request, body)
            if not endpoint:
                return web.json_response({"error": "Missing endpoint"}, status=400)
            if not client_token:
                return web.json_response({"error": "Unauthorized"}, status=401)
            deleted = await pm.delete_subscription(endpoint, client_token)
            if not deleted:
                return web.json_response({"error": "Unauthorized or not found"}, status=401)
            return web.json_response({"status": "unsubscribed"})
        except Exception as e:
            logger.error(f"PUSH_UNSUBSCRIBE_ERROR: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        sync_started = time.perf_counter()
        history_rows = 0
        active_count = len(self.active_events)

        try:
            history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
            history_rows = len(history)
            await ws.send_str(json.dumps({
                "type": "history_sync",
                "data": history,
                "has_more": has_more,
                "version": self.version,
            }))

            if self.active_events:
                events_list = await build_merged_payloads(self.active_events, self.engine, threshold_km=15)
                if events_list:
                    await ws.send_str(json.dumps({
                        "type": "multi_alert",
                        "events": events_list,
                    }, ensure_ascii=False))
            log_ws_session(
                event="CONNECT",
                client_count=len(self.clients),
                history_rows=history_rows,
                active_events=active_count,
                duration_ms=(time.perf_counter() - sync_started) * 1000,
            )
        except Exception as e:
            log_ws_session(
                event="CONNECT",
                client_count=len(self.clients),
                history_rows=history_rows,
                active_events=active_count,
                duration_ms=(time.perf_counter() - sync_started) * 1000,
                error=e,
            )

        try:
            async for msg in ws:
                pass
        finally:
            self.clients.discard(ws)
            log_ws_session(event="DISCONNECT", client_count=len(self.clients))
        return ws

    async def history_handler(self, request):
        # Support both 'category' (new protocol) and 'type' (legacy)
        category = request.query.get("category") or request.query.get("type")
        hours = request.query.get("hours")
        limit_raw = request.query.get("limit")
        offset_raw = request.query.get("offset")

        view = (request.query.get("view") or "list").lower()
        slim = view != "full"

        limit = 50
        if hours and hours != 'all' and not slim:
            limit = 1000  # Full-detail time windows only (operator tools)
        if limit_raw is not None:
            try:
                limit = max(1, min(1000, int(limit_raw)))
            except ValueError:
                pass
        offset = 0
        if offset_raw is not None:
            try:
                offset = max(0, int(offset_raw))
            except ValueError:
                pass

        paged = request.query.get("page") == "1"

        started = time.perf_counter()
        has_more = None
        if category:
            if paged:
                history, has_more = await self.db.get_history_page(
                    alert_type=category, limit=limit, hours=hours, offset=offset, slim=slim,
                )
            else:
                history = await self.db.get_history(
                    alert_type=category, limit=limit, hours=hours, offset=offset, slim=slim,
                )
        elif paged:
            history, has_more = await self.db.get_consolidated_history_page(
                limit=limit, hours=hours, offset=offset, slim=slim,
            )
        else:
            history = await self.db.get_consolidated_history(
                limit=limit, hours=hours, offset=offset, slim=slim,
            )
        duration_ms = (time.perf_counter() - started) * 1000
        log_history_fetch(
            category=category,
            limit=limit,
            offset=offset,
            row_count=len(history),
            payload_bytes=estimate_json_bytes(history),
            duration_ms=duration_ms,
        )
        if paged:
            return web.json_response({
                "items": history,
                "has_more": has_more,
                "next_offset": offset + len(history),
            })
        return web.json_response(history)

    async def history_event_handler(self, request):
        event_id = request.query.get("id")
        if not event_id:
            return web.json_response({"error": "Missing id"}, status=400)
        category = request.query.get("category") or request.query.get("type")
        doc = await self.db.find_history_event(event_id, category=category or None)
        if not doc:
            return web.json_response({"error": "Not found"}, status=404)
        return web.json_response(doc)

    async def cities_handler(self, request):
        return web.json_response(self.engine.dm.areas)

    async def calibrate_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            return web.json_response({"status": "SUCCESS"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def update_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            alert_id = data.get("id")
            alert_type = data.get("category")
            origin_name = data.get("origin_name")
            marker_coords = data.get("origin_coords") # Usually from UI drag
            
            if not all([alert_id, alert_type, origin_name, marker_coords]):
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            # Fetch existing to recalculate
            existing = await self.db.get_alert(alert_id, alert_type)
            if not existing:
                return web.json_response({"error": "Alert not found"}, status=404)

            # 1. Update Title and Origin labels
            display_origin = "Iran" if origin_name == "North Iran" else origin_name
            existing["title"] = f"{display_origin} Salvo" if alert_type == "missiles" else existing["title"]
            existing["verified"] = True
            existing["manual_origin"] = origin_name
            existing["verified_at"] = datetime.now(TIMEZONE).isoformat()
            if data.get("origin_ml_scores") is not None:
                existing["origin_ml_scores"] = data.get("origin_ml_scores")
            
            # Update Zoom Level (root and trajectory for dual-consumer compatibility)
            zoom = self.engine.zoom_levels.get(origin_name, self.engine.zoom_levels.get("Iran", 6) if "Iran" in origin_name else 8)
            existing["zoom_level"] = zoom

            # 2. Update Clusters
            if existing.get("clusters"):
                for cluster in existing["clusters"]:
                    cluster["origin"] = origin_name

            # 3. Recalculate trajectory if Missiles
            if alert_type == "missiles" and existing.get("trajectories"):
                traj = existing["trajectories"][0]
                cities = existing.get("all_cities") or []
                sync_missile_trajectory_on_verify(traj, origin_name, marker_coords, cities, self.engine)
                existing["trajectories"] = [traj]
                target = traj.get("target_coords")
                if target:
                    existing["center"] = target
                logger.info(
                    f"HISTORY_RECALC: {alert_id} verified trajectory "
                    f"{marker_coords} -> {target} ({origin_name})"
                )

            # 4. Commit FULL synchronized payload
            await self.db.save_alert(alert_type, existing)
            
            logger.info(f"HISTORY_FIXED_FULL: {alert_id} ({alert_type}) synchronized to {origin_name} by operator.")
            # Broadcast history refresh
            history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
            await self.broadcast({
                "type": "history_sync", "data": history, "has_more": has_more,
            })
            return web.json_response({"status": "SUCCESS", "event": existing})
            
        except Exception as e:
            logger.error(f"HISTORY_UPDATE_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def split_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            alert_id = data.get("id")
            alert_type = data.get("category")
            
            if not all([alert_id, alert_type]):
                return web.json_response({"error": "Missing required fields"}, status=400)
            
            success = await self.db.split_alert(alert_type, alert_id)
            if success:
                logger.info(f"HISTORY_SPLIT: {alert_id} ({alert_type}) removed for re-processing.")
                # Broadcast history refresh
                history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
                await self.broadcast({
                    "type": "history_sync", "data": history, "has_more": has_more,
                })
                return web.json_response({"status": "SUCCESS"})
            else:
                return web.json_response({"error": "Split failed"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def merge_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            data = await request.json()
            alert_ids = data.get("ids")
            alert_category = data.get("category")
            
            if not alert_ids or not alert_category or not isinstance(alert_ids, list):
                return web.json_response({"error": "Invalid IDs or category"}, status=400)
            
            if len(alert_ids) < 2:
                return web.json_response({"error": "Select at least two events to merge"}, status=400)
                
            master_payload = await self.db.merge_alerts(alert_category, alert_ids, self.engine)
            
            if master_payload:
                logger.info(f"HISTORY_MANUAL_MERGE: {len(alert_ids)} events consolidated -> {master_payload['id']}")
                # Broadcast history refresh
                history, has_more = await self.db.get_consolidated_history_page(limit=50, slim=True)
                await self.broadcast({
                    "type": "history_sync", "data": history, "has_more": has_more,
                })
                return web.json_response({"status": "SUCCESS", "event": master_payload})
            else:
                return web.json_response({"error": "Merge failed"}, status=500)
                
        except Exception as e:
            logger.error(f"HISTORY_MERGE_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def _cities_from_suggest_request(self, data):
        alert_id = data.get("id")
        alert_type = data.get("category", "missiles")
        if alert_id:
            existing = await self.db.get_alert(alert_id, alert_type)
            if not existing:
                return None, None
            return existing.get("all_cities") or [], existing

        from src.utils.text_utils import standardize_name
        raw = data.get("cities") or []
        mapped = []
        for c in raw:
            std = standardize_name(c if isinstance(c, str) else c.get("name"))
            if std and std in self.engine.dm.city_map:
                entry = self.engine.dm.city_map[std]
                mapped.append({
                    "name": entry.get("name") or c,
                    "coords": [entry["lat"], entry["lon"]],
                    "area": entry.get("area", "Other"),
                })
        return mapped, None

    async def suggest_origin_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)

            data = await request.json()
            cities, existing = await self._cities_from_suggest_request(data)
            if cities is None:
                return web.json_response({"error": "Alert not found"}, status=404)
            if not cities:
                return web.json_response({"error": "No cities to analyze"}, status=400)

            allow_strategic = bool(data.get("allow_strategic", True))
            raw_clusters = self.engine.cluster(cities)
            candidates = []
            for rc in raw_clusters:
                org, _ = await self.engine.get_origin(rc["cities"], allow_strategic=allow_strategic)
                label = org.strip()
                if label not in candidates:
                    candidates.append(label)

            if len(candidates) < 2 and existing:
                traj_origins = [
                    t.get("origin") for t in (existing.get("trajectories") or [])
                    if t.get("origin")
                ]
                for o in traj_origins:
                    if o not in candidates:
                        candidates.append(o)

            scores = {}
            suggested = candidates[0] if candidates else "Unknown"
            confidence = 0.0
            resolved_by = "geometry"

            if len(candidates) >= 2:
                from src.core.origin_ml import resolve_origin_ml
                suggested, confidence, scores, resolved_by = await resolve_origin_ml(
                    self.engine, cities, candidates
                )
            elif candidates:
                from src.core.origin_ml import score_origin_candidate
                await self.engine._sync_verified_history()
                scores = {candidates[0]: score_origin_candidate(cities, candidates[0], self.engine.verified_history)}

            all_origins = list(candidates)
            if suggested and suggested not in all_origins:
                all_origins.append(suggested)
            entries = entry_by_origin(self.engine, cities, all_origins)

            return web.json_response({
                "candidates": candidates,
                "scores": scores,
                "suggested": suggested,
                "confidence": confidence,
                "resolved_by": resolved_by,
                "entry_by_origin": entries,
            })
        except Exception as e:
            logger.error(f"SUGGEST_ORIGIN_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def project_entry_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)

            data = await request.json()
            origin_name = (data.get("origin_name") or "").strip()
            if not origin_name:
                return web.json_response({"error": "origin_name required"}, status=400)

            cities, _ = await self._cities_from_suggest_request(data)
            if cities is None:
                return web.json_response({"error": "Alert not found"}, status=404)
            if not cities:
                return web.json_response({"error": "No cities to analyze"}, status=400)

            coords = project_entry_for_origin(self.engine, cities, origin_name)
            if not coords:
                return web.json_response({"error": "Could not project entry"}, status=400)

            return web.json_response({"origin_name": origin_name, "origin_coords": coords})
        except Exception as e:
            logger.error(f"PROJECT_ENTRY_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def origin_replay_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)

            from src.core.origin_replay import build_origin_replay
            from src.utils.config import MAX_IRAN_THRESHOLD

            data = await request.json()
            cities, existing = await self._cities_from_suggest_request(data)
            if cities is None:
                return web.json_response({"error": "Alert not found"}, status=404)
            if not cities:
                return web.json_response({"error": "No cities to analyze"}, status=400)

            allow_strategic = bool(data.get("allow_strategic", True))
            if "allow_strategic" not in data and existing:
                allow_strategic = True

            total_unique = len({c.get("name") for c in cities if c.get("name")})
            force_iran = total_unique > MAX_IRAN_THRESHOLD and allow_strategic

            replay = await build_origin_replay(
                self.engine,
                cities,
                allow_strategic=allow_strategic,
                force_iran=force_iran,
                stored=existing,
            )

            stored_origin = None
            stored_trajectories = None
            event_id = data.get("id")
            if existing:
                event_id = existing.get("id", event_id)
                trajs = existing.get("trajectories") or []
                stored_trajectories = trajs
                if trajs:
                    stored_origin = trajs[0].get("origin")

            return web.json_response({
                "event_id": event_id,
                "stored_origin": stored_origin,
                "stored_trajectories": stored_trajectories,
                "replay": replay,
            })
        except Exception as e:
            logger.error(f"ORIGIN_REPLAY_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def training_export_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)

            category = request.query.get("category", "missiles")
            fmt = request.query.get("format", "json")
            rows = await self.db.get_training_export(alert_type=category)

            if fmt == "csv":
                import csv
                import io
                buf = io.StringIO()
                if rows:
                    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
                    writer.writeheader()
                    for row in rows:
                        row_copy = dict(row)
                        row_copy["city_names"] = "|".join(row_copy.get("city_names") or [])
                        writer.writerow(row_copy)
                return web.Response(
                    text=buf.getvalue(),
                    content_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=training_export.csv"},
                )
            return web.json_response({"count": len(rows), "records": rows})
        except Exception as e:
            logger.error(f"TRAINING_EXPORT_HANDLER_FAILURE: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def broadcast(self, data):
        if not self.clients: return
        message = json.dumps(data, ensure_ascii=False)
        for client in list(self.clients):
            try: await client.send_str(message)
            except: self.clients.discard(client)

    async def start(self):
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self.port)
        await self._site.start()
        logger.info(f"TACTICAL_API_SERVICES_LISTENING: Port {self.port}")

    async def stop(self):
        runner = getattr(self, "_runner", None)
        if runner is not None:
            await runner.cleanup()
            self._runner = None
