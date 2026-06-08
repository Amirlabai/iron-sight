"""History fixer / origin replay HTTP routes — shared by full backend and operator server."""

import csv
import io
import logging
import os
import time
from datetime import datetime

from aiohttp import web

from src.utils.config import MAX_IRAN_THRESHOLD, MISSION_KEY, TIMEZONE
from src.utils.observability import estimate_json_bytes, log_history_fetch
from src.utils.trajectory_utils import (
    entry_by_origin,
    project_entry_for_origin,
    sync_missile_trajectory_on_verify,
)

logger = logging.getLogger("IronSightBackend")

OPERATOR_MODE = os.getenv("IRON_SIGHT_OPERATOR") == "1"


class HistoryOperatorAPI:
    def __init__(self, db, engine, *, on_history_mutate=None, operator_mode=None):
        self.db = db
        self.engine = engine
        self.on_history_mutate = on_history_mutate
        self.operator_mode = OPERATOR_MODE if operator_mode is None else operator_mode

    def register_routes(self, add_route):
        add_route("GET", "/api/history", self.history_handler)
        add_route("GET", "/api/history/event", self.history_event_handler)
        add_route("GET", "/api/cities", self.cities_handler)
        add_route("POST", "/api/history/update", self.update_history_handler)
        add_route("POST", "/api/history/split", self.split_history_handler)
        add_route("POST", "/api/history/merge", self.merge_history_handler)
        add_route("POST", "/api/history/suggest-origin", self.suggest_origin_handler)
        add_route("POST", "/api/history/project-entry", self.project_entry_handler)
        add_route("POST", "/api/origin/replay", self.origin_replay_handler)
        add_route("GET", "/api/history/training-export", self.training_export_handler)

    async def _notify_history_mutate(self):
        if self.on_history_mutate:
            await self.on_history_mutate()

    async def history_handler(self, request):
        category = request.query.get("category") or request.query.get("type")
        hours = request.query.get("hours")
        limit_raw = request.query.get("limit")
        offset_raw = request.query.get("offset")

        view_param = request.query.get("view")
        if view_param:
            view = view_param.lower()
        elif self.operator_mode:
            view = "full"
        else:
            view = "list"
        slim = view != "full"

        limit = 50
        if hours and hours != "all" and not slim:
            limit = 1000
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

    async def update_history_handler(self, request):
        try:
            if MISSION_KEY and request.headers.get("X-Mission-Key") != MISSION_KEY:
                return web.json_response({"error": "Unauthorized"}, status=401)

            data = await request.json()
            alert_id = data.get("id")
            alert_type = data.get("category")
            origin_name = data.get("origin_name")
            marker_coords = data.get("origin_coords")

            if not all([alert_id, alert_type, origin_name, marker_coords]):
                return web.json_response({"error": "Missing required fields"}, status=400)

            existing = await self.db.get_alert(alert_id, alert_type)
            if not existing:
                return web.json_response({"error": "Alert not found"}, status=404)

            display_origin = "Iran" if origin_name == "North Iran" else origin_name
            existing["title"] = f"{display_origin} Salvo" if alert_type == "missiles" else existing["title"]
            existing["verified"] = True
            existing["manual_origin"] = origin_name
            existing["verified_at"] = datetime.now(TIMEZONE).isoformat()
            if data.get("origin_ml_scores") is not None:
                existing["origin_ml_scores"] = data.get("origin_ml_scores")

            zoom = self.engine.zoom_levels.get(
                origin_name,
                self.engine.zoom_levels.get("Iran", 6) if "Iran" in origin_name else 8,
            )
            existing["zoom_level"] = zoom

            if existing.get("clusters"):
                for cluster in existing["clusters"]:
                    cluster["origin"] = origin_name

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

            await self.db.save_alert(alert_type, existing)

            logger.info(f"HISTORY_FIXED_FULL: {alert_id} ({alert_type}) synchronized to {origin_name} by operator.")
            await self._notify_history_mutate()
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
                await self._notify_history_mutate()
                return web.json_response({"status": "SUCCESS"})
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
                await self._notify_history_mutate()
                return web.json_response({"status": "SUCCESS", "event": master_payload})
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
