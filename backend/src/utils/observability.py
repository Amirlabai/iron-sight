"""Operational logging helpers: RSS memory, HTTP timing, payload size."""

import json
import logging
import sys
import time

from aiohttp import web

try:
    import resource
except ImportError:
    resource = None

logger = logging.getLogger("IronSightTerminal")


def rss_mb():
    """Process RSS in MB. Linux Render: ru_maxrss is KiB; macOS: bytes."""
    if resource is None:
        return None
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return round(usage / (1024 * 1024), 1)
        return round(usage / 1024, 1)
    except Exception:
        return None


def rss_suffix():
    mb = rss_mb()
    return f" rss_mb={mb}" if mb is not None else ""


def estimate_json_bytes(payload):
    """Rough serialized size without retaining a second full copy when possible."""
    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        return None


def response_body_bytes(response):
    body = getattr(response, "body", None)
    if body is not None:
        return len(body)
    text = getattr(response, "text", None)
    if text is not None:
        return len(text.encode("utf-8"))
    return 0


@web.middleware
async def http_observability_middleware(request, handler):
    """Log method, path, status, bytes, duration, and RSS for HTTP handlers."""
    if request.path == "/ws" or request.path.startswith("/api/history"):
        return await handler(request)  # history routes log via HISTORY_FETCH / event handler

    started = time.perf_counter()
    try:
        response = await handler(request)
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            f"HTTP {request.method} {request.path} "
            f"status={response.status} bytes={response_body_bytes(response)} "
            f"duration_ms={duration_ms:.0f}{rss_suffix()}"
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.error(
            f"HTTP {request.method} {request.path} failed "
            f"duration_ms={duration_ms:.0f}{rss_suffix()}: {exc}",
            exc_info=True,
        )
        raise


def log_runtime_banner(*, version, relay_enabled, port, python_version=None):
    py = python_version or sys.version.split()[0]
    relay = "enabled" if relay_enabled else "disabled"
    logger.info(
        f"RUNTIME: python={py} version={version} port={port} relay={relay}{rss_suffix()}"
    )


def log_relay_poll(*, alert_count, changed, store_members, store_masters=None, unique_cities=None):
    parts = [
        f"RELAY_POLL: alerts={alert_count}",
        f"changed={str(changed).lower()}",
        f"active={store_members}",
    ]
    if store_masters is not None:
        parts.append(f"masters={store_masters}")
    if unique_cities is not None:
        parts.append(f"cities={unique_cities}")
    logger.info(" ".join(parts) + rss_suffix())


def log_broadcast(*, event_count, cache_hit, payload_bytes=None):
    cache = "hit" if cache_hit else "miss"
    msg = f"BROADCAST: events={event_count} cache={cache}"
    if payload_bytes is not None:
        msg += f" bytes={payload_bytes}"
    logger.info(msg + rss_suffix())


def log_history_fetch(*, category, limit, offset, row_count, payload_bytes, duration_ms):
    cat = category or "all"
    logger.info(
        f"HISTORY_FETCH: category={cat} limit={limit} offset={offset} "
        f"rows={row_count} bytes={payload_bytes} duration_ms={duration_ms:.0f}{rss_suffix()}"
    )


def log_ws_session(*, event, client_count, history_rows=None, active_events=None, duration_ms=None, error=None):
    msg = f"WS_{event}: clients={client_count}"
    if history_rows is not None:
        msg += f" history_rows={history_rows}"
    if active_events is not None:
        msg += f" active_events={active_events}"
    if duration_ms is not None:
        msg += f" sync_ms={duration_ms:.0f}"
    if error:
        logger.error(f"{msg}{rss_suffix()}: {error}", exc_info=True)
    else:
        logger.info(msg + rss_suffix())
