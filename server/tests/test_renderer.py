"""Snapshot tests for server/renderer.py.

Renders each model_*.json fixture and compares the SHA-256 of the output BMP
against a stored snapshot under tests/snapshots/. To intentionally update
snapshots after a renderer change, set UPDATE_SNAPSHOTS=1 in the env.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from renderer import render_to_bmp  # noqa: E402
from night_mode import render_night_mode  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class RendererSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _check_snapshot(self, snapshot_name: str, current_path: Path) -> None:
        snap = SNAPSHOTS_DIR / snapshot_name
        if os.environ.get("UPDATE_SNAPSHOTS") == "1":
            SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy(current_path, snap)
            print(f"[update] wrote {snap}")
            return
        if not snap.exists():
            self.fail(
                f"missing snapshot {snap} — run with UPDATE_SNAPSHOTS=1 to create it"
            )
        actual = sha256_of(current_path)
        expected = sha256_of(snap)
        self.assertEqual(
            actual, expected,
            f"{snapshot_name} drifted from snapshot. Inspect both BMPs and, if "
            "the change is intentional, re-run with UPDATE_SNAPSHOTS=1.",
        )

    def test_each_fixture_matches_snapshot(self) -> None:
        fixtures = sorted(FIXTURES_DIR.glob("model_*.json"))
        self.assertGreater(len(fixtures), 0, "no fixtures found in tests/fixtures")
        for fx in fixtures:
            with self.subTest(fixture=fx.name):
                with fx.open(encoding="utf-8") as f:
                    model = json.load(f)
                out = self.tmp / f"{fx.stem}.bmp"
                render_to_bmp(model, str(out))
                self._check_snapshot(fx.with_suffix(".bmp").name.replace("model_", "render_"), out)

    def test_night_mode_snapshot(self) -> None:
        out = self.tmp / "render_night_mode.bmp"
        render_night_mode(str(out))
        self._check_snapshot("render_night_mode.bmp", out)


if __name__ == "__main__":
    unittest.main()
