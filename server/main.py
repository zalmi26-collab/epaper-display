"""Entry point — runs every hour from GitHub Actions (and manually for dev).

Pipeline:
  1. Fetch weather, Hebcal calendar, Google Calendar events.
  2. Build the unified data model (server/builder.py).
  3. Render the day OR night view through web/screen.jsx (Playwright).
     Night mode (00:00..05:00) is handled inside screen.jsx — main.py just
     hands off the data model and the renderer takes care of the routing.
  4. Write the result to output/display.bmp for gh-pages publishing.

Exit codes:
  0 — success, BMP written
  1 — at least one critical fetcher failed AND we have no stale image to keep
  2 — unexpected exception
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# Local imports (executed as `python server/main.py` from project root)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from builder import JERUSALEM_TZ, build_data_model
from config import CALENDAR_ID, OUTPUT_DAY_BMP, OUTPUT_DIR, SERVICE_ACCOUNT_PATH
from fetchers.gcal import fetch_events
from fetchers.hebcal import fetch_hebcal
from fetchers.weather import fetch_weather
from renderer import render_to_bmp

logger = logging.getLogger("epaper")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(JERUSALEM_TZ)
    logger.info("Run started at %s", now.isoformat())

    weather = fetch_weather()
    logger.info("weather: %s", "ok" if weather else "FAIL")

    hebcal = fetch_hebcal(now.date(), days=8)
    logger.info("hebcal: %s", "ok" if hebcal else "FAIL")

    events = None
    if CALENDAR_ID:
        events = fetch_events(CALENDAR_ID, service_account_path=SERVICE_ACCOUNT_PATH)
        logger.info("calendar: %s", f"{len(events)} events" if events is not None else "FAIL")
    else:
        logger.warning("CALENDAR_ID not set — skipping calendar fetch")

    # If both critical fetchers failed, abort and let the ESP32 keep showing the
    # previous image (gh-pages branch isn't updated → display.bmp is stale).
    if weather is None and hebcal is None:
        logger.error("Both weather and hebcal failed — aborting without writing BMP")
        return 1

    data = build_data_model(weather, hebcal, events, now)
    logger.info(
        "model: night_mode=%s shabbat=%s timed=%d all_day=%d omer=%s weather_kind=%s",
        data["night_mode"],
        bool(data["shabbat"]),
        len(data["timed_events"]),
        len(data["all_day_events"]),
        bool(data["omer"]),
        data["weather_kind"],
    )

    render_to_bmp(data, str(OUTPUT_DAY_BMP))
    logger.info("Wrote %s", OUTPUT_DAY_BMP)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logger.exception("Unhandled error in main()")
        sys.exit(2)
