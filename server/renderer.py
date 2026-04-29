"""Renderer — Headless Chromium pipeline for the e-paper display.

The visual design lives in ``web/screen.jsx`` (a React component) and
``web/render.html`` (a single-screen page that mounts it). This module is a
thin wrapper that:

  1. Spins up an in-process HTTP server rooted at ``web/`` so Babel's
     ``<script type="text/babel" src="screen.jsx">`` request isn't blocked by
     CORS (it would be, if we used a ``file://`` URL).
  2. Launches Playwright Chromium (headless).
  3. Pre-populates ``window.SCREEN_DATA`` with the model dict.
  4. Loads ``http://127.0.0.1:<port>/render.html``.
  5. Waits until ``window.SCREEN_READY === true`` (fonts loaded + React mounted
     + the 1-bit threshold SVG filter rasterized).
  6. Screenshots the 800x480 ``#artboard`` element.
  7. Thresholds the PNG to a 1-bit BMP at the requested path.

The CSS-level threshold filter inside ``render.html`` already snaps every
pixel to pure black/white at the 50% line, so the Pillow conversion below is
mostly bookkeeping (BMP container, color depth = 1).

Output: 800x480 1-bit BMP. The clock area (520..800 x 0..120) is left blank
by the design; the ESP32 firmware overlays the live minute on top.
"""

from __future__ import annotations

import http.server
import io
import json
import logging
import socketserver
import threading
from contextlib import contextmanager
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

CANVAS_W = 800
CANVAS_H = 480

# The ESP32 overlays the clock here — keep it blank in the design.
CLOCK_AREA = (520, 0, 800, 120)

# Locate web/ relative to this file (server/renderer.py → ../web/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"
RENDER_HTML = WEB_DIR / "render.html"

# How long to wait for fonts + React to settle before screenshotting.
# Google Fonts CDN is the slowest dependency; 30s is generous.
READY_TIMEOUT_MS = 30_000


@contextmanager
def _serve_dir(directory: Path):
    """Serve `directory` over HTTP on a random localhost port for the duration
    of the context. Yields the port number.

    Why an HTTP server instead of ``file://``: Babel-standalone fetches the
    ``<script type="text/babel" src="screen.jsx">`` via XMLHttpRequest, and
    Chromium blocks XHRs on ``file://`` origins under CORS. A localhost server
    sidesteps that without bundling the project."""
    handler = lambda *a, **kw: _QuietHandler(*a, directory=str(directory), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that doesn't spam stdout per request."""

    def log_message(self, format, *args):  # noqa: A002 (matching parent signature)
        return


def render_to_bmp(data: dict, output_path: str) -> None:
    """Render the data model to a 1-bit BMP at the given path.

    Args:
        data: the model produced by ``builder.build_data_model``. Must match
            the schema expected by ``web/screen.jsx`` (see ``builder.py`` for
            the field list).
        output_path: where to write the BMP. Existing files are overwritten.
    """
    if not RENDER_HTML.exists():
        raise FileNotFoundError(
            f"render.html missing at {RENDER_HTML}. The web/ directory must ship "
            "alongside server/."
        )

    png_bytes = _capture_artboard_png(data)

    # Convert to 1-bit BMP. The threshold filter inside render.html already
    # snapped pixels to black/white, but Pillow needs us to explicitly request
    # a 1bpp BMP — Image.save() won't downconvert from RGBA to 1-bit on its own.
    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    if img.size != (CANVAS_W, CANVAS_H):
        # Defensive: Playwright should clip to viewport, but if it ever doesn't
        # we'd rather catch it loudly than write a wrong-size BMP.
        raise RuntimeError(
            f"Screenshot dimensions {img.size} != expected ({CANVAS_W}, {CANVAS_H})"
        )
    bw = img.point(lambda v: 255 if v >= 128 else 0, mode="1")
    bw.save(output_path, format="BMP")
    logger.info("Wrote %sx%s 1-bit BMP to %s", CANVAS_W, CANVAS_H, output_path)


def _capture_artboard_png(data: dict) -> bytes:
    """Spin up Chromium, mount the screen with `data`, return a PNG of #artboard."""
    # Serialize once outside the browser (json.dumps with ensure_ascii=False
    # preserves Hebrew niqqud bytes). Then inject as a JS global before the
    # page scripts run.
    init_js = f"window.SCREEN_DATA = {json.dumps(data, ensure_ascii=False)};"

    with _serve_dir(WEB_DIR) as port, sync_playwright() as p:
        url = f"http://127.0.0.1:{port}/render.html"
        # `chromium.launch()` defaults to headless. We pin viewport to exactly
        # the artboard size so device pixel ratio = 1 (no fractional rounding
        # at the 1-bit threshold step).
        browser = p.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": CANVAS_W, "height": CANVAS_H},
                device_scale_factor=1,
            )
            context.add_init_script(init_js)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("window.SCREEN_READY === true", timeout=READY_TIMEOUT_MS)

            artboard = page.locator("#artboard")
            png_bytes = artboard.screenshot(type="png", omit_background=False)
        finally:
            browser.close()

    return png_bytes


if __name__ == "__main__":
    """Render every fixture under tests/fixtures/ for visual review."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fixtures_dir = Path(__file__).resolve().parent / "tests" / "fixtures"
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    fixtures = sorted(fixtures_dir.glob("model_*.json"))
    if not fixtures:
        print("No fixtures found under tests/fixtures/. Generate some first.")
        sys.exit(1)

    for fx in fixtures:
        with fx.open(encoding="utf-8") as f:
            model = json.load(f)
        out = output_dir / fx.with_suffix(".bmp").name.replace("model_", "render_")
        render_to_bmp(model, str(out))
        print(f"  {fx.name} -> {out}")
