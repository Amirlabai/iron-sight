"""Slim operator API for history-fixer / origin replay — no relay, WS, or push."""

import asyncio
import json
import logging
import os
from datetime import datetime

from aiohttp import web
import aiohttp_cors

from src.api.history_operator import HistoryOperatorAPI
from src.core.engine import TrackingEngine
from src.data.data_manager import LamasDataManager
from src.db.mongo_manager import MongoManager
from src.utils.config import ALLOWED_ORIGINS, OPERATOR_PORT, TIMEZONE

os.environ.setdefault("IRON_SIGHT_OPERATOR", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s",
)
logger = logging.getLogger("IronSightOperator")

VERSION = "0.0.0"
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "..", "version.json"), "r") as f:
        VERSION = json.load(f).get("version", "0.0.0")
except Exception:
    pass


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _history_fixer_dist():
    return os.path.join(_repo_root(), "history-fixer", "dist")


def _setup_static(app):
    dist = _history_fixer_dist()
    index = os.path.join(dist, "index.html")
    if not os.path.isfile(index):
        return

    async def spa_index(_request):
        return web.FileResponse(index)

    async def spa_asset(request):
        rel = request.match_info.get("path", "")
        target = os.path.normpath(os.path.join(dist, rel))
        if not target.startswith(os.path.normpath(dist)) or not os.path.isfile(target):
            return await spa_index(request)
        return web.FileResponse(target)

    app.router.add_get("/assets/{path:.*}", spa_asset)
    app.router.add_get("/{path:.*}", spa_index)
    logger.info("OPERATOR_STATIC: serving history-fixer/dist at /")


async def run_operator():
    logger.info(f"IRON SIGHT OPERATOR CONSOLE (v{VERSION}) — history + replay API")

    db = MongoManager()
    dm = LamasDataManager()
    await dm.load()
    engine = TrackingEngine(dm, db)

    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        origin: aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        ) for origin in ALLOWED_ORIGINS
    })

    def add_route(method, path, handler):
        resource = app.router.add_resource(path)
        cors.add(resource.add_route(method, handler))

    history_api = HistoryOperatorAPI(db, engine, on_history_mutate=None, operator_mode=True)
    history_api.register_routes(add_route)

    async def health_handler(_request):
        return web.json_response({
            "status": "OPERATIONAL",
            "mode": "operator",
            "version": VERSION,
            "timestamp": datetime.now(TIMEZONE).isoformat(),
        })

    add_route("GET", "/api/health", health_handler)
    if os.path.isfile(os.path.join(_history_fixer_dist(), "index.html")):
        _setup_static(app)
    else:
        add_route("GET", "/", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", OPERATOR_PORT)
    await site.start()
    logger.info(f"OPERATOR_API_LISTENING: Port {OPERATOR_PORT}")

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


def main():
    try:
        asyncio.run(run_operator())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
