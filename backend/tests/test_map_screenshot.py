import pytest

from src.services.map_screenshot import MapCaptureResult, capture_map_png


def test_map_capture_result_complete():
    assert MapCaptureResult(png=b"x", tiles_ok=4, tiles_total=4).complete
    assert not MapCaptureResult(png=None, tiles_ok=3, tiles_total=4).complete
    assert not MapCaptureResult(png=b"x", tiles_ok=0, tiles_total=0).complete


@pytest.mark.asyncio
async def test_capture_fails_closed_on_missing_tile(monkeypatch):
    async def fake_fetch(_session, _zoom, x, y):
        if (x + y) % 2 == 0:
            return None
        from PIL import Image

        return Image.new("RGB", (256, 256), (20, 20, 20))

    monkeypatch.setattr("src.services.map_screenshot._fetch_tile", fake_fetch)
    result = await capture_map_png(32.71999, 35.44193, zoom=12, size_px=256)
    assert not result.complete
    assert result.png is None
    assert result.tiles_ok < result.tiles_total


@pytest.mark.asyncio
async def test_capture_clamps_tile_indices(monkeypatch):
    seen = []

    async def fake_fetch(_session, zoom, x, y):
        seen.append((x, y))
        from PIL import Image

        return Image.new("RGB", (256, 256), (30, 30, 30))

    monkeypatch.setattr("src.services.map_screenshot._fetch_tile", fake_fetch)
    await capture_map_png(85.0, 0.0, zoom=3, size_px=512)
    max_tile = (2 ** 3) - 1
    assert all(0 <= x <= max_tile and 0 <= y <= max_tile for x, y in seen)
