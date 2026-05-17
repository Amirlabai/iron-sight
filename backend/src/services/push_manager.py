import asyncio
import json
import logging
import secrets
from pywebpush import webpush, WebPushException

from src.utils.config import (
    VAPID_PUBLIC_KEY,
    VAPID_PRIVATE_KEY,
    VAPID_CLAIMS_EMAIL,
)
from src.utils.alert_matching import (
    matches_alert_scope,
    build_alert_notify_key,
    format_push_body,
    ALLOWED_SCOPES,
    clamp_radius_km,
)

logger = logging.getLogger("IronSightPush")

MAX_LAST_NOTIFIED_ENTRIES = 50
_PUSH_SEND_SEM = asyncio.Semaphore(10)


def _send_webpush_sync(subscription_info, payload, vapid_claims):
    webpush(
        subscription_info=subscription_info,
        data=payload,
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims=vapid_claims,
    )


def _prune_last_notified(last_notified, active_alert_ids):
    if not last_notified:
        return {}
    pruned = {k: v for k, v in last_notified.items() if k in active_alert_ids}
    if len(pruned) > MAX_LAST_NOTIFIED_ENTRIES:
        keys = list(pruned.keys())[-MAX_LAST_NOTIFIED_ENTRIES:]
        pruned = {k: pruned[k] for k in keys}
    return pruned


class PushManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self._vapid_ready = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)

    def is_configured(self):
        return self._vapid_ready and self.db is not None and self.db.db is not None

    def get_vapid_public_key(self):
        return VAPID_PUBLIC_KEY

    async def upsert_subscription(self, body):
        if not self.is_configured():
            return False, "Push service unavailable", None
        sub = body.get("subscription") or {}
        endpoint = sub.get("endpoint")
        keys = sub.get("keys") or {}
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            return False, "Invalid subscription", None

        scope = body.get("scope", "all")
        if scope not in ALLOWED_SCOPES:
            return False, "Invalid scope", None

        radius_km = clamp_radius_km(body.get("radius_km", 10))

        loc = body.get("location")
        location = None
        if loc and loc.get("lat") is not None and loc.get("lng") is not None:
            location = [float(loc["lat"]), float(loc["lng"])]

        existing = await self.db.get_push_subscription(endpoint)
        client_token = (existing or {}).get("client_token") or secrets.token_urlsafe(32)

        doc = {
            "endpoint": endpoint,
            "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]},
            "scope": scope,
            "radius_km": radius_km,
            "location": location,
            "client_token": client_token,
            "last_notified": (existing or {}).get("last_notified") or {},
        }
        await self.db.upsert_push_subscription(doc)
        return True, None, client_token

    async def update_location(self, endpoint, lat, lng, client_token):
        if not self.db or not self.db.db:
            return "unavailable"
        if not await self.db.verify_push_client(endpoint, client_token):
            return "unauthorized"
        matched = await self.db.update_push_location(endpoint, float(lat), float(lng))
        if not matched:
            return "not_found"
        return "ok"

    async def delete_subscription(self, endpoint, client_token):
        if not self.db:
            return False
        if not await self.db.verify_push_client(endpoint, client_token):
            return False
        return await self.db.delete_push_subscription(endpoint)

    async def _send_one(self, subscription_info, payload, vapid_claims):
        async with _PUSH_SEND_SEM:
            await asyncio.to_thread(
                _send_webpush_sync,
                subscription_info,
                payload,
                vapid_claims,
            )

    async def notify_matching_subscriptions(self, events):
        if not self.is_configured() or not events:
            return

        subs = await self.db.list_push_subscriptions()
        if not subs:
            return

        vapid_claims = {"sub": VAPID_CLAIMS_EMAIL}
        active_alert_ids = {e.get("id") for e in events if e.get("id")}

        for event in events:
            if event.get("category") == "newsFlash":
                continue

            title = f"IRON SIGHT — {event.get('title', 'Alert')}"
            body = format_push_body(event)
            notify_key = build_alert_notify_key(event)
            alert_id = event.get("id", "")

            payload = json.dumps(
                {
                    "title": title,
                    "body": body,
                    "alertId": alert_id,
                    "url": "/",
                },
                ensure_ascii=False,
            )

            for sub in subs:
                scope = sub.get("scope", "all")
                location = sub.get("location")
                radius_km = sub.get("radius_km", 10)

                if not matches_alert_scope(location, event, scope, radius_km):
                    continue

                last = sub.get("last_notified") or {}
                if last.get(alert_id) == notify_key:
                    continue

                subscription_info = {
                    "endpoint": sub["endpoint"],
                    "keys": sub["keys"],
                }

                try:
                    await self._send_one(subscription_info, payload, vapid_claims)
                    if sub.get("last_notified") is None:
                        sub["last_notified"] = {}
                    sub["last_notified"][alert_id] = notify_key
                    pruned = _prune_last_notified(sub["last_notified"], active_alert_ids)
                    sub["last_notified"] = pruned
                    await self.db.set_last_notified(sub["endpoint"], pruned)
                except WebPushException as ex:
                    status = getattr(ex, "response", None)
                    code = status.status_code if status is not None else None
                    if code in (404, 410):
                        await self.db.delete_push_subscription(sub["endpoint"])
                        logger.info(f"PUSH_SUB_EXPIRED: removed {sub['endpoint'][:48]}...")
                    else:
                        logger.warning(f"PUSH_SEND_FAIL: {code} {ex}")
