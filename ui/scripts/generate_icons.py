"""Generate the PWA icons (icon-192.png, icon-512.png) with no dependencies.

Draws a full-bleed rounded-square in the Onni brand colour (#1F3864) with the
"◎" ring mark (white ring + centre dot, echoing the app's nav logo) kept inside
the maskable safe zone (centre 66% of the canvas, well within the 80% circle
that maskable icons may be cropped to). Corners outside the rounded square are
transparent so the same file also works for purpose "any".

Usage:
    python3 ui/scripts/generate_icons.py

Writes ui/public/icons/icon-192.png and ui/public/icons/icon-512.png.
"""

from __future__ import annotations

import logging
import math
import pathlib
import struct
import zlib

logger = logging.getLogger(__name__)

BRAND_RGB = (0x1F, 0x38, 0x64)  # brand navy (#1F3864)
WHITE_RGB = (0xFF, 0xFF, 0xFF)
SIZES = (192, 512)
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "public" / "icons"


def _rounded_rect_coverage(x: float, y: float, size: float, radius: float) -> float:
    """Return 0..1 coverage of the pixel centre by a full-bleed rounded square.

    Args:
        x: Pixel-centre x coordinate.
        y: Pixel-centre y coordinate.
        size: Canvas size in pixels (square).
        radius: Corner radius in pixels.

    Returns:
        Anti-aliased coverage in [0, 1] (1 = fully inside the shape).
    """
    # Signed distance to a rounded rectangle centred on the canvas.
    half = size / 2.0
    qx = abs(x - half) - (half - radius)
    qy = abs(y - half) - (half - radius)
    dist = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - radius
    return min(1.0, max(0.0, 0.5 - dist))  # 1px anti-alias band


def _ring_coverage(x: float, y: float, size: float) -> float:
    """Return 0..1 white coverage for the ◎ mark (ring + centre dot).

    Args:
        x: Pixel-centre x coordinate.
        y: Pixel-centre y coordinate.
        size: Canvas size in pixels (square).

    Returns:
        Anti-aliased coverage in [0, 1] of the white glyph at this pixel.
    """
    half = size / 2.0
    d = math.hypot(x - half, y - half)
    ring_outer = size * 0.30   # glyph stays inside the centre 60% (safe zone)
    ring_inner = size * 0.22
    dot_radius = size * 0.10
    # Ring band coverage
    ring = min(1.0, max(0.0, 0.5 - (d - ring_outer))) * \
        min(1.0, max(0.0, 0.5 - (ring_inner - d)))
    # Centre dot coverage
    dot = min(1.0, max(0.0, 0.5 - (d - dot_radius)))
    return max(ring, dot)


def _render_rgba(size: int) -> bytes:
    """Render the icon as raw RGBA scanlines (with PNG filter byte 0).

    Args:
        size: Canvas size in pixels (square).

    Returns:
        Raw bytes ready for zlib compression into a PNG IDAT chunk.
    """
    radius = size * 0.20
    rows = bytearray()
    for py in range(size):
        rows.append(0)  # filter type 0 (None)
        y = py + 0.5
        for px in range(size):
            x = px + 0.5
            shape = _rounded_rect_coverage(x, y, size, radius)
            glyph = _ring_coverage(x, y, size)
            r, g, b = (
                round(BRAND_RGB[i] + (WHITE_RGB[i] - BRAND_RGB[i]) * glyph)
                for i in range(3)
            )
            rows.extend((r, g, b, round(255 * shape)))
    return bytes(rows)


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    """Build one PNG chunk (length + tag + payload + CRC).

    Args:
        tag: Four-byte chunk type, e.g. ``b"IHDR"``.
        payload: Chunk payload bytes.

    Returns:
        The serialized chunk.
    """
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_icon(size: int, path: pathlib.Path) -> None:
    """Render and write one PNG icon.

    Args:
        size: Canvas size in pixels (square).
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(_render_rgba(size), 9)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    logger.info("wrote %s (%d bytes)", path, len(png))


def main() -> None:
    """Generate all icon sizes into ui/public/icons/."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        write_icon(size, OUT_DIR / f"icon-{size}.png")


if __name__ == "__main__":
    main()
