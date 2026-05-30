"""Static map PNG at a lat/lng + zoom (Carto dark tiles, no browser)."""

import asyncio
import logging
import math
from dataclasses import dataclass
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw

logger = logging.getLogger("IronSightBackend")

TILE_SIZE = 256
CARTO_DARK = "https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png"
DEFAULT_ZOOM = 12
DEFAULT_SIZE = 640
@dataclass(frozen=True)
class MapCaptureResult:
    png: bytes | None
    tiles_ok: int
    tiles_total: int

    @property
    def complete(self) -> bool:
        return (
            self.tiles_total > 0
            and self.tiles_ok == self.tiles_total
            and self.png is not None
        )


def _lat_lng_to_world_px(lat: float, lng: float, zoom: int) -> tuple[float, float]:
    scale = TILE_SIZE * (2 ** zoom)
    x = (lng + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(lat))
    sin_lat = max(min(sin_lat, 0.9999), -0.9999)
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


async def _fetch_tile(session: aiohttp.ClientSession, zoom: int, x: int, y: int):
    url = CARTO_DARK.format(z=zoom, x=x, y=y)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning("MAP_TILE_FETCH_FAIL: HTTP %s for %s/%s/%s", resp.status, zoom, x, y)
                return None
            data = await resp.read()
            with Image.open(BytesIO(data)) as im:
                return im.convert("RGB").copy()
    except Exception as exc:
        logger.warning("MAP_TILE_FETCH_FAIL: %s %s/%s/%s — %s", zoom, x, y, exc)
        return None


async def capture_map_png(
    lat: float,
    lng: float,
    *,
    zoom: int = DEFAULT_ZOOM,
    size_px: int = DEFAULT_SIZE,
    marker_color: str = "#ff3b30",
    session: aiohttp.ClientSession | None = None,
) -> MapCaptureResult:
    """Compose a square PNG centered on lat/lng. Fails closed if any tile is missing."""
    center_x, center_y = _lat_lng_to_world_px(lat, lng, zoom)
    half = size_px / 2
    top_left_x = center_x - half
    top_left_y = center_y - half
    bottom_right_x = center_x + half
    bottom_right_y = center_y + half

    min_tx = int(math.floor(top_left_x / TILE_SIZE))
    max_tx = int(math.floor((bottom_right_x - 1) / TILE_SIZE))
    min_ty = int(math.floor(top_left_y / TILE_SIZE))
    max_ty = int(math.floor((bottom_right_y - 1) / TILE_SIZE))
    max_tile = (2 ** zoom) - 1
    min_tx = max(0, min(min_tx, max_tile))
    max_tx = max(0, min(max_tx, max_tile))
    min_ty = max(0, min(min_ty, max_tile))
    max_ty = max(0, min(max_ty, max_tile))

    canvas = Image.new("RGB", (size_px, size_px), (10, 10, 12))
    coords = [
        (tx, ty)
        for ty in range(min_ty, max_ty + 1)
        for tx in range(min_tx, max_tx + 1)
    ]
    tiles_total = len(coords)

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(headers={"User-Agent": "IronSight/1.0"})

    try:
        tiles = await asyncio.gather(
            *[_fetch_tile(session, zoom, tx, ty) for tx, ty in coords],
        )
    finally:
        if own_session:
            await session.close()

    tiles_ok = 0
    for (tx, ty), tile in zip(coords, tiles):
        if tile is None:
            continue
        tiles_ok += 1
        paste_x = int(tx * TILE_SIZE - top_left_x)
        paste_y = int(ty * TILE_SIZE - top_left_y)
        canvas.paste(tile, (paste_x, paste_y))

    if tiles_ok < tiles_total or tiles_total == 0:
        logger.warning(
            "MAP_CAPTURE_INCOMPLETE: %s/%s tiles for zoom %s center %.4f,%.4f",
            tiles_ok,
            tiles_total,
            zoom,
            lat,
            lng,
        )
        return MapCaptureResult(png=None, tiles_ok=tiles_ok, tiles_total=tiles_total)

    marker_px = int(center_x - top_left_x), int(center_y - top_left_y)
    draw = ImageDraw.Draw(canvas, "RGBA")
    r_outer = 28
    r_inner = 14
    draw.ellipse(
        [
            marker_px[0] - r_outer,
            marker_px[1] - r_outer,
            marker_px[0] + r_outer,
            marker_px[1] + r_outer,
        ],
        outline=_hex_to_rgba(marker_color, 180),
        width=3,
    )
    draw.ellipse(
        [
            marker_px[0] - r_inner,
            marker_px[1] - r_inner,
            marker_px[0] + r_inner,
            marker_px[1] + r_inner,
        ],
        fill=_hex_to_rgba(marker_color, 90),
        outline=_hex_to_rgba(marker_color, 220),
        width=2,
    )

    out = BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return MapCaptureResult(
        png=out.getvalue(),
        tiles_ok=tiles_ok,
        tiles_total=tiles_total,
    )


def _hex_to_rgba(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    h = (hex_color or "#ff3b30").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        r, g, b = 255, 59, 48
    return r, g, b, alpha
