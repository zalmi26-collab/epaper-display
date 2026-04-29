"""Renderer tests.

Note on snapshots: the previous Pillow renderer rendered byte-deterministically
across machines, so we used SHA-256 snapshots. The new renderer goes through
headless Chromium, where rendering varies slightly across Chromium versions
and platforms (font hinting, sub-pixel positioning). Snapshot-by-hash would be
flaky in CI for cosmetic reasons.

Instead these tests assert the *structural* invariants the firmware cares
about: the BMP exists at the requested path, has the right dimensions, is
1-bit, and contains both black and white pixels (i.e., the screen actually
rendered — not a blank canvas)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from renderer import CANVAS_H, CANVAS_W, render_to_bmp  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render(self, fixture_name: str) -> Path:
        fixture = FIXTURES_DIR / fixture_name
        with fixture.open(encoding="utf-8") as f:
            data = json.load(f)
        out = self.tmp / fixture.with_suffix(".bmp").name
        render_to_bmp(data, str(out))
        return out

    def _assert_valid_bmp(self, path: Path) -> Image.Image:
        self.assertTrue(path.exists(), f"BMP not written to {path}")
        img = Image.open(path)
        self.assertEqual(img.mode, "1", "BMP must be 1-bit (mode '1')")
        self.assertEqual(
            img.size, (CANVAS_W, CANVAS_H),
            f"BMP must be {CANVAS_W}x{CANVAS_H}, got {img.size}",
        )
        return img

    def _assert_not_blank(self, img: Image.Image) -> None:
        # `1`-mode images return 0 (black) and 255 (white). A blank screen
        # would only have 255s. Confirm both colors are present.
        colors = img.getcolors()
        self.assertIsNotNone(colors, "Could not enumerate BMP colors")
        values = sorted(c[1] for c in colors)
        self.assertEqual(values, [0, 255], f"BMP has only {values} — looks blank")

    def test_weekday_renders(self) -> None:
        path = self._render("model_now.json")
        img = self._assert_valid_bmp(path)
        self._assert_not_blank(img)

    def test_thursday_morning_renders(self) -> None:
        # Thursday morning: shabbat strip should appear (visibility window opens
        # Thu 06:00). The renderer doesn't expose layout, but at minimum the
        # render must succeed and produce a non-blank canvas.
        path = self._render("model_thursday_morning.json")
        img = self._assert_valid_bmp(path)
        self._assert_not_blank(img)

    def test_friday_evening_renders(self) -> None:
        path = self._render("model_friday_evening.json")
        img = self._assert_valid_bmp(path)
        self._assert_not_blank(img)

    def test_night_mode_renders(self) -> None:
        # Night mode (00:00..05:00) routes to NightScreen — the canvas is
        # mostly black with the clock/moon highlights in white.
        path = self._render("model_night.json")
        img = self._assert_valid_bmp(path)
        self._assert_not_blank(img)
        # Sanity: night mode is dominated by black pixels.
        colors = dict((v, n) for n, v in img.getcolors())
        black = colors.get(0, 0)
        white = colors.get(255, 0)
        self.assertGreater(
            black, white,
            "night mode should be majority-black "
            f"(got black={black}, white={white})",
        )


if __name__ == "__main__":
    unittest.main()
