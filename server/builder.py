"""Builder — merge fetcher outputs into the unified display data model.

The output schema is documented in the spec section 5. This module is the only
place that decides:
  - whether to show the Shabbat / holiday box
  - whether to include the Omer count
  - which calendar events are still upcoming
  - whether to switch to night mode

All time comparisons are done in Asia/Jerusalem (the displayed timezone).
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timedelta
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

JERUSALEM_TZ = pytz.timezone("Asia/Jerusalem")

# Mon=0 .. Sun=6 (Python's weekday convention)
HEBREW_WEEKDAYS = {
    0: "יום שני",
    1: "יום שלישי",
    2: "יום רביעי",
    3: "יום חמישי",
    4: "יום שישי",
    5: "שבת",
    6: "יום ראשון",
}

NIGHT_MODE_START_HOUR = 23  # 23:00 (inclusive)
NIGHT_MODE_END_HOUR = 5     # 05:00 (exclusive)

# Display-window rules for the Shabbat / holiday box
SHABBAT_BOX_THURSDAY_START_HOUR = 6   # Friday Shabbat: visible from Thu 06:00
HOLIDAY_BOX_SAME_DAY_START_HOUR = 12  # Other holidays: visible from candles_day 12:00

CLOCK_AREA = {"x": 520, "y": 0, "width": 280, "height": 120}


def build_data_model(
    weather: Optional[dict],
    hebcal: Optional[dict],
    events: Optional[list[dict]],
    now: Optional[datetime] = None,
) -> dict:
    """Build the JSON data model the renderer consumes.

    Args:
        weather: dict from fetchers.weather.fetch_weather(), or None on failure.
        hebcal: dict from fetchers.hebcal.fetch_hebcal(), or None on failure.
        events: list from fetchers.gcal.fetch_events(), or None / [] if none.
        now: timezone-aware reference time. Defaults to current time in Asia/Jerusalem.

    Returns:
        dict matching the spec schema. Missing data is represented as None.
    """
    if now is None:
        now = datetime.now(JERUSALEM_TZ)
    elif now.tzinfo is None:
        now = JERUSALEM_TZ.localize(now)
    else:
        now = now.astimezone(JERUSALEM_TZ)

    today_iso = now.date().isoformat()
    today_hebcal = (hebcal.get("by_date", {}) if hebcal else {}).get(today_iso, {})

    return {
        "generated_at": now.replace(microsecond=0).isoformat(),
        "next_update_at": _next_hour(now).isoformat(),
        "clock_area": CLOCK_AREA,
        "date": {
            "gregorian": now.strftime("%d.%m.%Y"),
            "hebrew": today_hebcal.get("hebrew_date"),
            "weekday_he": today_hebcal.get("weekday_he") or HEBREW_WEEKDAYS[now.weekday()],
        },
        "weather": _normalize_weather(weather),
        "shabbat_box": _build_shabbat_box(hebcal, now),
        "events_timed": _build_events_timed(events, now),
        "events_all_day": _build_events_all_day(events, now),
        "omer": _build_omer(today_hebcal),
        "night_mode": _is_night_mode(now),
    }


def _normalize_weather(weather: Optional[dict]) -> Optional[dict]:
    if not weather:
        return None
    return {
        "city": "בית שמש",
        "temp_max": weather.get("temp_max"),
        "temp_min": weather.get("temp_min"),
        "precipitation_chance": weather.get("precipitation_chance"),
        "sunrise": weather.get("sunrise"),
        "sunset": weather.get("sunset"),
    }


def _build_shabbat_box(hebcal: Optional[dict], now: datetime) -> Optional[dict]:
    """Decide whether to show the Shabbat / holiday box and build it.

    Window rules:
      - Friday Shabbat: from Thursday 06:00 → that Saturday's havdalah
      - Other holidays: from candles_day 12:00 → that holiday's havdalah
    """
    if not hebcal:
        return None
    by_date = hebcal.get("by_date", {})
    today = now.date()

    # Find the next havdalah at or after today
    havdalah_date = None
    havdalah_time = None
    for date_str in sorted(by_date.keys()):
        d = datetime.fromisoformat(date_str).date()
        if d < today:
            continue
        info = by_date[date_str]
        if info.get("havdalah"):
            havdalah_date = d
            havdalah_time = info["havdalah"]
            break
    if havdalah_date is None:
        return None

    # Find the most recent candles on or before that havdalah
    candles_date = None
    candles_time = None
    candles_info: dict = {}
    for date_str in sorted(by_date.keys()):
        d = datetime.fromisoformat(date_str).date()
        if d > havdalah_date:
            break
        info = by_date[date_str]
        if info.get("candles"):
            candles_date = d
            candles_time = info["candles"]
            candles_info = info
    if candles_date is None:
        return None

    # Compute the start of the visibility window
    is_friday_shabbat = candles_date.weekday() == 4
    if is_friday_shabbat:
        start_naive = datetime.combine(
            candles_date - timedelta(days=1),
            dtime(SHABBAT_BOX_THURSDAY_START_HOUR, 0),
        )
    else:
        start_naive = datetime.combine(
            candles_date, dtime(HOLIDAY_BOX_SAME_DAY_START_HOUR, 0)
        )
    start = JERUSALEM_TZ.localize(start_naive)

    # End of window: havdalah moment
    h_h, h_m = _split_hhmm(havdalah_time)
    end = JERUSALEM_TZ.localize(datetime.combine(havdalah_date, dtime(h_h, h_m)))

    if not (start <= now <= end):
        return None

    havdalah_info = by_date.get(havdalah_date.isoformat(), {})
    title, is_holiday = _shabbat_box_title(candles_info, havdalah_info, is_friday_shabbat)

    return {
        "title": title,
        "candles": candles_time,
        "sunset": _approx_sunset_from_candles(candles_time),
        "havdalah": havdalah_time,
        "is_holiday": is_holiday,
    }


def _shabbat_box_title(
    candles_info: dict, havdalah_info: dict, is_friday_shabbat: bool
) -> tuple[str, bool]:
    """Pick the right title for the Shabbat / holiday box.

    Only "major" holidays (Pesach Day 1, Shavuot, Rosh Hashana, etc.) are the
    real reason candles are lit — those override the parasha title. Minor /
    modern / fast / Rosh Chodesh holidays that happen to coincide with Shabbat
    don't change the title.

    Returns (title, is_holiday).
    """
    parashah = havdalah_info.get("parashah") or candles_info.get("parashah")

    major_holiday = None
    for info in (candles_info, havdalah_info):
        if info.get("holiday") and info.get("holiday_subcat") == "major":
            major_holiday = info["holiday"]
            break

    if major_holiday:
        return major_holiday, True
    if is_friday_shabbat and parashah:
        return parashah, False
    if parashah:
        return parashah, False
    fallback_holiday = candles_info.get("holiday") or havdalah_info.get("holiday")
    if fallback_holiday:
        return fallback_holiday, True
    return "שבת", False


def _approx_sunset_from_candles(candles_hhmm: str) -> str:
    """Approximate sunset = candles + 18 minutes (typical Israeli minhag)."""
    h, m = _split_hhmm(candles_hhmm)
    total = h * 60 + m + 18
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def _build_events_timed(events: Optional[list[dict]], now: datetime) -> list[dict]:
    """Return upcoming timed events (today + tomorrow), sorted chronologically.

    Schema: {"start": "HH:MM", "title": "...", "is_tomorrow": bool}.
    is_tomorrow lets the renderer disambiguate '14:30 today' from '14:30 tomorrow'.
    """
    if not events:
        return []
    today = now.date()
    upcoming = []
    for ev in events:
        if ev.get("all_day"):
            continue
        try:
            start_dt = _parse_iso_to_jerusalem(ev["start"])
        except (KeyError, TypeError, ValueError):
            continue
        if start_dt <= now:
            continue
        upcoming.append((start_dt, ev["title"]))
    upcoming.sort(key=lambda pair: pair[0])
    return [
        {
            "start": dt.strftime("%H:%M"),
            "title": title,
            "is_tomorrow": dt.date() > today,
        }
        for dt, title in upcoming
    ]


def _build_events_all_day(events: Optional[list[dict]], now: datetime) -> list[dict]:
    """Return all-day events whose date is today or tomorrow."""
    if not events:
        return []
    today = now.date()
    tomorrow = today + timedelta(days=1)
    out = []
    for ev in events:
        if not ev.get("all_day"):
            continue
        try:
            start_date = datetime.fromisoformat(ev["start"]).date()
            end_date = datetime.fromisoformat(ev["end"]).date()
        except (KeyError, TypeError, ValueError):
            continue
        # Google Calendar all-day end is exclusive; an event on today ends "tomorrow".
        if end_date <= today:
            continue
        if start_date > tomorrow:
            continue
        out.append({"title": ev["title"]})
    return out


def _build_omer(today_hebcal: dict) -> Optional[dict]:
    day = today_hebcal.get("omer_day")
    if day is None:
        return None
    return {"day": day, "text": today_hebcal.get("omer_text")}


def _is_night_mode(now: datetime) -> bool:
    h = now.astimezone(JERUSALEM_TZ).hour
    return h >= NIGHT_MODE_START_HOUR or h < NIGHT_MODE_END_HOUR


def _next_hour(now: datetime) -> datetime:
    return (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))


def _parse_iso_to_jerusalem(value: str) -> datetime:
    """Parse an ISO datetime string to a timezone-aware datetime in Asia/Jerusalem."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = JERUSALEM_TZ.localize(dt)
    return dt.astimezone(JERUSALEM_TZ)


def _split_hhmm(hhmm: str) -> tuple[int, int]:
    h, m = hhmm.split(":")
    return int(h), int(m)


if __name__ == "__main__":
    """Manual smoke test using live fetcher output."""
    import json
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.path.insert(0, str(Path(__file__).parent))
    from fetchers.weather import fetch_weather
    from fetchers.hebcal import fetch_hebcal

    weather = fetch_weather()
    hebcal = fetch_hebcal(datetime.now(JERUSALEM_TZ).date(), days=8)
    # Calendar likely None without creds — test resilience
    events = None

    model = build_data_model(weather, hebcal, events)
    print(json.dumps(model, indent=2, ensure_ascii=False))
