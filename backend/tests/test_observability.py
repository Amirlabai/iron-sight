from src.utils.observability import estimate_json_bytes, response_body_bytes, rss_mb


def test_estimate_json_bytes():
    assert estimate_json_bytes([{"id": "a"}]) > 0


def test_response_body_bytes_json():
    from aiohttp import web

    resp = web.json_response({"ok": True})
    assert response_body_bytes(resp) > 0


def test_rss_mb_optional():
    # May be None on some platforms; must not raise.
    mb = rss_mb()
    assert mb is None or mb >= 0
