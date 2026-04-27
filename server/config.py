"""Project configuration constants and runtime settings.

Public values live as module attributes; secrets come from environment
variables / files that are never committed.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Location ─────────────────────────────────────────────────────────────────
LATITUDE = 31.7497
LONGITUDE = 34.9886
TIMEZONE = "Asia/Jerusalem"
GEONAME_ID = 295089  # Bet Shemesh (used by Hebcal)
CITY_NAME_HE = "בית שמש"

# ── Refresh schedule ────────────────────────────────────────────────────────
NIGHT_MODE_START_HOUR = 23
NIGHT_MODE_END_HOUR = 5

# ── Output paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DAY_BMP = OUTPUT_DIR / "display.bmp"  # the file the ESP32 downloads

# ── Secrets / env-driven settings ───────────────────────────────────────────
SERVICE_ACCOUNT_PATH = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_PATH",
    str(PROJECT_ROOT / "secrets" / "service_account.json"),
).strip()
# strip whitespace — GitHub Secrets sometimes carry a trailing newline that
# breaks downstream URL building (404 from the Calendar API).
CALENDAR_ID = os.environ.get("CALENDAR_ID", "").strip()
