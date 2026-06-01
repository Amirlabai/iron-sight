"""Shared rules for outbound channels (push, Telegram) that must not fan out simulation."""


def skip_outbound_event(event) -> bool:
    return bool(event and event.get("is_simulation"))


def relay_upstream_label(relay_url: str, batch: list) -> str:
    if batch and any(a.get("is_simulation") for a in batch):
        return "SIMULATOR"
    url = (relay_url or "").lower()
    if "127.0.0.1" in url or "localhost" in url:
        return "SIMULATOR"
    return "LIVE"
