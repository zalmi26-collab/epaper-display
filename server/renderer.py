"""Renderer — Pillow-based BMP renderer for the e-paper display.

This is the functional/mock layout: every field from the data model is shown
in a clearly labeled region, but the visual design is intentionally plain.
A separate design pass (Claude Design) will replace this file later without
touching the data flow.

Output: 800×480 1-bit BMP. The clock_area in the top-right (520..800 × 0..120)
is left blank — the ESP32 firmware overlays the current minute on top.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

CANVAS_W = 800
CANVAS_H = 480

# The ESP32 overlays the clock here — keep it blank.
CLOCK_AREA = (520, 0, 800, 120)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FRANK_PATH = str(FONTS_DIR / "FrankRuhlLibre-Bold.ttf")
HEEBO_PATH = str(FONTS_DIR / "Heebo-Regular.ttf")


class FontBook:
    """Lazy-loaded font cache keyed by (family, size)."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get(self, family: str, size: int) -> ImageFont.FreeTypeFont:
        key = (family, size)
        if key not in self._cache:
            path = FRANK_PATH if family == "frank" else HEEBO_PATH
            self._cache[key] = ImageFont.truetype(path, size)
        return self._cache[key]


def render_to_bmp(data: dict, output_path: str) -> None:
    """Render the data model to a 1-bit BMP at the given path."""
    # Render in 'L' (8-bit grayscale) for crisp anti-aliased text, then
    # threshold-convert to '1' (1-bit) without dithering for clean output.
    img = Image.new("L", (CANVAS_W, CANVAS_H), 255)
    draw = ImageDraw.Draw(img)
    fonts = FontBook()

    _draw_top_row(draw, fonts, data["date"])
    cursor_y = 120
    draw.line([(0, cursor_y), (CANVAS_W, cursor_y)], fill=0, width=1)

    cursor_y = _draw_weather_and_shabbat_row(draw, fonts, data, top=cursor_y + 5)
    draw.line([(0, cursor_y), (CANVAS_W, cursor_y)], fill=0, width=1)

    cursor_y = _draw_all_day_events(draw, fonts, data["events_all_day"], top=cursor_y + 5)
    draw.line([(0, cursor_y), (CANVAS_W, cursor_y)], fill=0, width=1)

    cursor_y = _draw_timed_events(draw, fonts, data["events_timed"], top=cursor_y + 5)
    draw.line([(0, cursor_y), (CANVAS_W, cursor_y)], fill=0, width=1)

    cursor_y = _draw_omer(draw, fonts, data.get("omer"), top=cursor_y + 5)
    draw.line([(0, cursor_y), (CANVAS_W, cursor_y)], fill=0, width=1)

    _draw_indicators(draw, fonts, data, top=cursor_y + 5)

    bw = img.convert("1", dither=Image.Dither.NONE)
    bw.save(output_path, format="BMP")
    logger.info("Wrote %s × %s 1-bit BMP to %s", CANVAS_W, CANVAS_H, output_path)


# ─── helpers ──────────────────────────────────────────────────────────────────


def _draw_text_rtl(
    draw: ImageDraw.ImageDraw,
    text: str,
    right_top_xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: int = 0,
) -> int:
    """Draw Hebrew (or mixed) text right-aligned. Returns drawn width."""
    visual = get_display(text)
    draw.text(right_top_xy, visual, font=font, fill=fill, anchor="rt")
    bbox = font.getbbox(visual)
    return bbox[2] - bbox[0]


def _draw_text_ltr(
    draw: ImageDraw.ImageDraw,
    text: str,
    left_top_xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: int = 0,
) -> int:
    """Draw left-to-right text. For pure numbers / Latin / dates."""
    draw.text(left_top_xy, text, font=font, fill=fill, anchor="lt")
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def _draw_text_mixed(
    draw: ImageDraw.ImageDraw,
    text: str,
    left_top_xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: int = 0,
) -> int:
    """Left-anchored text with bidi reordering — for time labels with Hebrew tags."""
    visual = get_display(text)
    draw.text(left_top_xy, visual, font=font, fill=fill, anchor="lt")
    bbox = font.getbbox(visual)
    return bbox[2] - bbox[0]


# ─── sections ─────────────────────────────────────────────────────────────────


def _draw_top_row(draw: ImageDraw.ImageDraw, fonts: FontBook, date: dict) -> None:
    """Top-left: date block. Top-right: clock area (left blank)."""
    # Date block fits in x: 10..510 (clock takes 520..800)
    hebrew = date.get("hebrew") or ""
    gregorian = date.get("gregorian") or ""
    weekday = date.get("weekday_he") or ""

    if hebrew:
        _draw_text_rtl(draw, hebrew, (510, 12), fonts.get("frank", 36))
    if weekday:
        _draw_text_rtl(draw, weekday, (510, 60), fonts.get("heebo", 26))
    if gregorian:
        _draw_text_ltr(draw, gregorian, (10, 60), fonts.get("heebo", 26))

    # CLOCK_AREA is intentionally left blank — the ESP32 firmware overlays the
    # current minute on top of this region (full refresh hourly + partial
    # refresh every minute).


def _draw_weather_and_shabbat_row(
    draw: ImageDraw.ImageDraw, fonts: FontBook, data: dict, top: int
) -> int:
    """Two-column row: weather on right (520..790), shabbat box on left (10..510)."""
    weather = data.get("weather") or {}
    shabbat = data.get("shabbat_box")
    section_height = 130
    bottom = top + section_height

    # Vertical separator between the two columns when both visible
    if shabbat:
        draw.line([(515, top), (515, bottom - 1)], fill=0, width=1)

    # ── Weather column (right): 520..790 ──
    _draw_text_rtl(draw, weather.get("city", ""), (790, top), fonts.get("frank", 26))
    big_temps = f"{weather.get('temp_max', '—')}°/{weather.get('temp_min', '—')}°"
    _draw_text_ltr(draw, big_temps, (540, top + 28), fonts.get("heebo", 44))

    rain_label = f"גשם {weather.get('precipitation_chance', 0)}%"
    _draw_text_rtl(draw, rain_label, (790, top + 78), fonts.get("heebo", 20))

    sun_line = (
        f"זריחה {weather.get('sunrise', '—')}   שקיעה {weather.get('sunset', '—')}"
    )
    _draw_text_rtl(draw, sun_line, (790, top + 103), fonts.get("heebo", 20))

    # ── Shabbat box column (left): 10..510 ──
    if shabbat:
        _draw_text_rtl(
            draw, shabbat.get("title", ""), (505, top), fonts.get("frank", 32)
        )
        rows = [
            ("נרות", shabbat.get("candles")),
            ("שקיעה", shabbat.get("sunset")),
            ("הבדלה", shabbat.get("havdalah")),
        ]
        for i, (label, value) in enumerate(rows):
            row_y = top + 45 + i * 28
            _draw_text_rtl(draw, label, (505, row_y), fonts.get("heebo", 22))
            _draw_text_ltr(draw, value or "—", (15, row_y), fonts.get("heebo", 22))

    return bottom


def _draw_all_day_events(
    draw: ImageDraw.ImageDraw, fonts: FontBook, events: list[dict], top: int
) -> int:
    """Thin strip with all-day event titles separated by bullets."""
    section_height = 30
    if not events:
        # Still leave the strip so layout stays predictable, but mark empty.
        _draw_text_rtl(draw, "אין אירועי כל-יום", (790, top + 4), fonts.get("heebo", 18), fill=128)
        return top + section_height

    titles = "  •  ".join(ev["title"] for ev in events)
    _draw_text_rtl(draw, titles, (790, top + 2), fonts.get("heebo", 22))
    return top + section_height


def _draw_timed_events(
    draw: ImageDraw.ImageDraw, fonts: FontBook, events: list[dict], top: int
) -> int:
    """List of timed events: HH:MM on the left, title on the right."""
    section_height = 110
    bottom = top + section_height

    if not events:
        _draw_text_rtl(
            draw, "אין אירועים עתידיים היום ומחר",
            (790, top + 50), fonts.get("heebo", 22), fill=128,
        )
        return bottom

    line_height = 30
    max_lines = section_height // line_height
    for i, ev in enumerate(events[:max_lines]):
        row_y = top + 2 + i * line_height
        time_label = ev["start"]
        if ev.get("is_tomorrow"):
            time_label += " (מחר)"
            _draw_text_mixed(draw, time_label, (10, row_y), fonts.get("heebo", 22))
        else:
            _draw_text_ltr(draw, time_label, (10, row_y), fonts.get("heebo", 22))
        # Truncate long titles roughly to the available width
        title = ev["title"]
        max_chars = 36
        if len(title) > max_chars:
            title = title[: max_chars - 1] + "…"
        _draw_text_rtl(draw, title, (790, row_y), fonts.get("heebo", 22))

    overflow = len(events) - max_lines
    if overflow > 0:
        _draw_text_rtl(
            draw, f"+ עוד {overflow} אירועים…",
            (790, top + section_height - 22), fonts.get("heebo", 18), fill=128,
        )

    return bottom


def _draw_omer(
    draw: ImageDraw.ImageDraw, fonts: FontBook, omer: Optional[dict], top: int
) -> int:
    section_height = 30
    if not omer:
        return top + section_height
    text = omer.get("text") or f"היום {omer.get('day')} ימים לעומר"
    # Frank Ruhl Libre handles full niqqud (vowel marks) where Heebo shows tofu.
    _draw_text_rtl(draw, text, (790, top + 2), fonts.get("frank", 22))
    return top + section_height


def _draw_indicators(
    draw: ImageDraw.ImageDraw, fonts: FontBook, data: dict, top: int
) -> None:
    """Bottom row: only the server-side refresh timestamp.

    The battery icon and error X are drawn by the ESP32 firmware on top of
    this BMP — the server intentionally leaves the bottom-left corner blank.
    """
    refresh_label = "עודכן: " + (data.get("generated_at") or "—")[11:16]
    _draw_text_rtl(draw, refresh_label, (790, top + 4), fonts.get("heebo", 18))


if __name__ == "__main__":
    """Render every fixture in tests/fixtures/ for visual review."""
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fixtures_dir = Path(__file__).resolve().parent / "tests" / "fixtures"
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    fixtures = sorted(fixtures_dir.glob("model_*.json"))
    if not fixtures:
        print("No fixtures found. Run builder.py first to generate them.")
        sys.exit(1)

    for fx in fixtures:
        with open(fx, encoding="utf-8") as f:
            model = json.load(f)
        out = output_dir / fx.with_suffix(".bmp").name.replace("model_", "render_")
        render_to_bmp(model, str(out))
        print(f"  {fx.name} → {out}")
