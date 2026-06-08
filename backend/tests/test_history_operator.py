import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
import aiohttp_cors

from src.api.history_operator import HistoryOperatorAPI


@pytest.fixture
def history_api():
    db = MagicMock()
    engine = MagicMock()
    return HistoryOperatorAPI(db, engine, on_history_mutate=None, operator_mode=True)


def _collect_routes(app):
    routes = set()
    for route in app.router.routes():
        for method in route.method.split(","):
            routes.add((method.strip().upper(), route.resource.canonical))
    return routes


def test_register_routes_includes_operator_endpoints(history_api):
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    def add_route(method, path, handler):
        resource = app.router.add_resource(path)
        cors.add(resource.add_route(method, handler))

    history_api.register_routes(add_route)
    routes = _collect_routes(app)

    assert ("GET", "/api/history") in routes
    assert ("POST", "/api/history/update") in routes
    assert ("POST", "/api/origin/replay") in routes
    assert ("GET", "/api/history/training-export") in routes


@pytest.mark.asyncio
async def test_update_without_mutate_callback_does_not_broadcast(history_api):
    history_api.db.get_alert = AsyncMock(return_value={
        "id": "1",
        "title": "Iran Salvo",
        "clusters": [],
        "trajectories": [{"origin": "Iran"}],
        "all_cities": [],
    })
    history_api.db.save_alert = AsyncMock()
    history_api.engine.zoom_levels = {"Iran": 6, "Yemen": 5}

    request = MagicMock()
    request.headers = {"X-Mission-Key": "test-key"}
    request.json = AsyncMock(return_value={
        "id": "1",
        "category": "missiles",
        "origin_name": "Yemen",
        "origin_coords": [15.0, 44.0],
    })

    with patch("src.api.history_operator.MISSION_KEY", "test-key"):
        resp = await history_api.update_history_handler(request)
    assert resp.status == 200
    history_api.db.save_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_operator_mode_defaults_view_full(history_api):
    history_api.db.get_consolidated_history = AsyncMock(return_value=[])
    request = MagicMock()
    request.query = {}

    await history_api.history_handler(request)

    history_api.db.get_consolidated_history.assert_awaited_once()
    assert history_api.db.get_consolidated_history.await_args.kwargs["slim"] is False
