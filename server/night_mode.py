"""Night-mode renderer — static "good night" image shown 23:00 → 05:00.

Layout: a large crescent moon with scattered stars, plus a "לילה טוב" greeting.
The clock area in the top-right is left blank — the ESP32 still draws the
current minute on top during sleep wake-ups, so people can see the time
without flooding the room with light.
"""

from __future__ import annotations

import logging
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

# Same one-shot bidi detection used by renderer.py — see that file for context.
HAS_RAQM = features.check("raqm")

CANVAS_W = 800
CANVAS_H = 480
CLOCK_AREA = (520, 0, 800, 120)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FRANK_PATH = str(FONTS_DIR / "FrankRuhlLibre-Bold.ttf")

GREETING_TEXT = "לילה טוב"


def render_night_mode(output_path: str) -> None:
    """Render the static night-mode BMP."""
    img = Image.new("L", (CANVAS_W, CANVAS_H), 255)
    draw = ImageDraw.Draw(img)

    _draw_stars(draw)
    _draw_moon(draw, center=(280, 230), radius=120)
    _draw_greeting(draw)

    bw = img.convert("1", dither=Image.Dither.NONE)
    bw.save(output_path, format="BMP")
    logger.info("Wrote night-mode BMP to %s", output_path)


def _draw_moon(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
    """Crescent moon: filled black circle with a white circle offset to carve it."""
    cx, cy = center
    # Outline + fill main disc
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=0, outline=0,
    )
    # Carve a white disc, offset to the upper-right, leaving a crescent on the left
    offset_x = int(radius * 0.45)
    offset_y = -int(radius * 0.20)
    inner_r = int(radius * 0.95)
    draw.ellipse(
        [cx + offset_x - inner_r, cy + offset_y - inner_r,
         cx + offset_x + inner_r, cy + offset_y + inner_r],
        fill=255,
    )


def _draw_stars(draw: ImageDraw.ImageDraw) -> None:
    """Scatter ~30 stars across the upper portion of the canvas (avoiding clock area)."""
    rng = random.Random(42)  # deterministic — same render every time
    placed: list[tuple[int, int]] = []
    attempts = 0
    while len(placed) < 30 and attempts < 500:
        attempts += 1
        x = rng.randint(20, CANVAS_W - 20)
        y = rng.randint(20, CANVAS_H - 80)
        # Avoid the reserved clock area
        if CLOCK_AREA[0] <= x <= CLOCK_AREA[2] and CLOCK_AREA[1] <= y <= CLOCK_AREA[3]:
            continue
        # Avoid the moon's bounding box
        if 140 <= x <= 420 and 90 <= y <= 370:
            continue
        # Spacing
        if any(math.hypot(x - px, y - py) < 50 for px, py in placed):
            continue
        size = rng.choice([6, 8, 10, 12])
        _draw_star(draw, x, y, size)
        placed.append((x, y))


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    """Draw a 4-pointed star (plus shape) centered at (cx, cy)."""
    # Plus / 4-point star: cleaner at 1-bit than 5-pointed polygons
    draw.line([(cx - size, cy), (cx + size, cy)], fill=0, width=2)
    draw.line([(cx, cy - size), (cx, cy + size)], fill=0, width=2)
    # Diagonal accents at half size for sparkle effect
    half = max(2, size // 2)
    draw.line([(cx - half, cy - half), (cx + half, cy + half)], fill=0, width=1)
    draw.line([(cx - half, cy + half), (cx + half, cy - half)], fill=0, width=1)


def _draw_greeting(draw: ImageDraw.ImageDraw) -> None:
    """Center a large 'לילה טוב' near the bottom."""
    font = ImageFont.truetype(FRANK_PATH, 96)
    if HAS_RAQM:
        rendered = GREETING_TEXT
        kwargs = {"direction": "rtl"}
    else:
        rendered = get_display(GREETING_TEXT, base_dir="R")
        kwargs = {}
    bbox = font.getbbox(rendered, **kwargs)
    text_w = bbox[2] - bbox[0]
    x = (CANVAS_W - text_w) // 2
    y = 380
    draw.text((x, y), rendered, font=font, fill=0, anchor="lt", **kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    output = Path(__file__).resolve().parent.parent / "output" / "render_night_mode.bmp"
    output.parent.mkdir(exist_ok=True)
    render_night_mode(str(output))
    Image.open(output).save(str(output).replace(".bmp", ".png"))
    print(f"wrote {output}")
