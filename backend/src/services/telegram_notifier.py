"""Telegram alerts when Kfar Kama (כפר כמא) is in an active threat event."""

import asyncio
import logging
from datetime import datetime

import aiohttp

from src.services.map_screenshot import capture_map_png, DEFAULT_ZOOM
from src.utils.config import (
    KFAR_KAMA_ALERT_LAT,
    KFAR_KAMA_ALERT_LNG,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_MAP_ZOOM,
    TIMEZONE,
)
from src.utils.kfar_kama import event_affects_kfar_kama, event_track_ids
from src.utils.outbound_policy import skip_outbound_event

logger = logging.getLogger("IronSightBackend")

_HTTP_HEADERS = {"User-Agent": "IronSight/1.0"}
_TELEGRAM_MAX_RETRIES = 3


class TelegramRateLimitError(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


_CATEGORY_COLORS = {
    "missiles": "#ff3b30",
    "hostileAircraftIntrusion": "#ff9500",
    "terroristInfiltration": "#bf5af2",
    "earthQuake": "#64d2ff",
    "newsFlash": "#ffcc00",
}

_CATEGORY_LABELS = {
    "missiles": "Missiles",
    "hostileAircraftIntrusion": "Hostile aircraft",
    "terroristInfiltration": "Infiltration",
    "earthQuake": "Earthquake",
    "newsFlash": "News flash",
}


class TelegramNotifier:
    def __init__(self):
        self._enabled = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        self._last_notify_key: dict[str, str] = {}
        self._started_alert_ids: set[str] = set()
        self._terminated_alert_ids: set[str] = set()
        self._session: aiohttp.ClientSession | None = None
        self._tile_session: aiohttp.ClientSession | None = None
        self._pending_tasks: set[asyncio.Task] = set()
        self._notify_lock = asyncio.Lock()
        if not self._enabled:
            logger.info("TELEGRAM: disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
        else:
            chat_hint = TELEGRAM_CHAT_ID[:4] if len(TELEGRAM_CHAT_ID) >= 4 else "?"
            logger.info("TELEGRAM: enabled for Kfar Kama alerts (chat_id=%s…)", chat_hint)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def close(self):
        for task in list(self._pending_tasks):
            task.cancel()
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
        self._pending_tasks.clear()
        for session_attr in ("_session", "_tile_session"):
            session = getattr(self, session_attr)
            if session and not session.closed:
                await session.close()
            setattr(self, session_attr, None)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=_HTTP_HEADERS)
        return self._session

    async def _get_tile_session(self) -> aiohttp.ClientSession:
        if self._tile_session is None or self._tile_session.closed:
            self._tile_session = aiohttp.ClientSession(headers=_HTTP_HEADERS)
        return self._tile_session

    @staticmethod
    def _should_skip_event(event) -> bool:
        return skip_outbound_event(event)

    def _notify_key(self, event) -> str:
        alert_id = event.get("id") or "unknown"
        category = event.get("category") or "alert"
        return f"{alert_id}|{category}"

    def _is_stale_active_event(self, event) -> bool:
        """True when END already ran while a scheduled notify was still queued."""
        track_ids = event_track_ids(event)
        return bool(track_ids.intersection(self._terminated_alert_ids))

    def schedule_notify_events_if_kfar_kama(self, events_list):
        """Non-blocking: tile fetch + Telegram must not stall relay loop."""
        if not self._enabled or not events_list:
            return
        task = asyncio.create_task(self._notify_events_safe(events_list))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _notify_events_safe(self, events_list):
        try:
            async with self._notify_lock:
                await self.notify_events_if_kfar_kama(events_list)
        except Exception as exc:
            self._log_send_error(exc)

    async def notify_events_if_kfar_kama(self, events_list):
        if not self._enabled or not events_list:
            return
        for event in events_list:
            if self._should_skip_event(event) or not event_affects_kfar_kama(event):
                continue
            alert_id = event.get("id")
            key = self._notify_key(event)
            if self._last_notify_key.get(alert_id) == key:
                continue
            if self._is_stale_active_event(event):
                continue
            try:
                if self._is_stale_active_event(event):
                    continue
                photo_sent = await self._send_kfar_kama_alert(event, started=True)
                if photo_sent:
                    if self._is_stale_active_event(event):
                        continue
                    self._last_notify_key[alert_id] = key
                    self._started_alert_ids.update(event_track_ids(event))
            except Exception as exc:
                self._log_send_error(exc)

    def clear_stale_keys(self, active_track_ids: set[str]):
        for aid in list(self._last_notify_key):
            if aid not in active_track_ids:
                del self._last_notify_key[aid]
        for aid in list(self._started_alert_ids):
            if aid not in active_track_ids and aid in self._terminated_alert_ids:
                self._started_alert_ids.discard(aid)
                self._terminated_alert_ids.discard(aid)

    async def notify_kfar_kama_terminated(self, event, alert_id=None):
        """Send when alert ends. Matches merged master id or any tracked sibling id."""
        if not self._enabled or not event:
            return
        if self._should_skip_event(event) or not event_affects_kfar_kama(event):
            return
        track_ids = event_track_ids(event, alert_id)
        if not self._started_alert_ids.intersection(track_ids):
            return
        try:
            async with self._notify_lock:
                if self._terminated_alert_ids.intersection(track_ids):
                    return
                if not self._started_alert_ids.intersection(track_ids):
                    return
                await self._send_kfar_kama_alert(event, started=False)
                self._terminated_alert_ids.update(track_ids)
                self._started_alert_ids -= track_ids
                for tid in track_ids:
                    self._last_notify_key.pop(tid, None)
        except Exception as exc:
            self._log_send_error(exc)

    def _log_send_error(self, exc: Exception):
        msg = str(exc)
        if "chat not found" in msg.lower():
            logger.error(
                "TELEGRAM_SEND_FAIL: chat not found — fix TELEGRAM_CHAT_ID. "
                "DM: message @BotFather bot, send /start, use getUpdates for your numeric id. "
                "Group: add bot to group, use group id (often negative)."
            )
        elif "429" in msg:
            logger.error("TELEGRAM_SEND_FAIL: rate limited after retries — %s", msg[:200])
        else:
            logger.error("TELEGRAM_SEND_FAIL: %s", exc, exc_info=True)

    async def _send_kfar_kama_alert(self, event, *, started: bool) -> bool:
        category = event.get("category") or "alert"
        label = _CATEGORY_LABELS.get(category, category)
        city_count = len(event.get("all_cities") or [])
        ts = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        phase = "ACTIVE" if started else "ENDED"
        caption = (
            f"Iron Sight — Kfar Kama (כפר כמא)\n"
            f"{phase} · {label} · {city_count} cities\n"
            f"{ts} (Israel)"
        )

        if not started:
            await self._send_message(caption)
            return False

        color = _CATEGORY_COLORS.get(category, "#ff3b30")
        zoom = TELEGRAM_MAP_ZOOM or DEFAULT_ZOOM
        tile_session = await self._get_tile_session()
        capture = await capture_map_png(
            KFAR_KAMA_ALERT_LAT,
            KFAR_KAMA_ALERT_LNG,
            zoom=zoom,
            marker_color=color,
            session=tile_session,
        )
        if not capture.complete:
            logger.warning(
                "TELEGRAM_MAP_CAPTURE_FAIL: %s/%s tiles — skipping ACTIVE notify",
                capture.tiles_ok,
                capture.tiles_total,
            )
            return False
        await self._send_photo(capture.png, caption, zoom=zoom)
        return True

    @staticmethod
    def _parse_retry_after(header_value: str | None) -> float | None:
        if not header_value:
            return None
        try:
            return max(1.0, float(header_value.strip()))
        except ValueError:
            return None

    async def _post_with_retry(self, coro_factory):
        last_error = None
        for attempt in range(_TELEGRAM_MAX_RETRIES):
            try:
                return await coro_factory()
            except TelegramRateLimitError as exc:
                last_error = exc
                if attempt >= _TELEGRAM_MAX_RETRIES - 1:
                    raise
                delay = exc.retry_after if exc.retry_after is not None else (2 ** attempt)
                await asyncio.sleep(delay)
            except RuntimeError as exc:
                if "429" not in str(exc) or attempt >= _TELEGRAM_MAX_RETRIES - 1:
                    raise
                last_error = exc
                await asyncio.sleep(2 ** attempt)
        raise last_error

    async def _raise_for_response(self, resp, label: str):
        body = await resp.text()
        if resp.status == 429:
            retry_after = self._parse_retry_after(resp.headers.get("Retry-After"))
            raise TelegramRateLimitError(
                f"{label} HTTP 429: {body[:300]}",
                retry_after=retry_after,
            )
        if resp.status != 200:
            raise RuntimeError(f"{label} HTTP {resp.status}: {body[:300]}")

    async def _send_photo(self, png_bytes: bytes, caption: str, *, zoom: int):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

        async def do_post():
            form = aiohttp.FormData()
            form.add_field("chat_id", TELEGRAM_CHAT_ID)
            form.add_field("caption", caption[:1024])
            form.add_field(
                "photo",
                png_bytes,
                filename=f"kfar-kama-z{zoom}.png",
                content_type="image/png",
            )
            session = await self._get_session()
            async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                await self._raise_for_response(resp, "sendPhoto")

        await self._post_with_retry(do_post)

    async def _send_message(self, text: str):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        async def do_post():
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text[:4096]}
            session = await self._get_session()
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                await self._raise_for_response(resp, "sendMessage")

        await self._post_with_retry(do_post)
