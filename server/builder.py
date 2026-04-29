"""Builder — merge fetcher outputs into the unified display data model.

The output schema matches what ``web/screen.jsx`` consumes (Nest-Hub style
Hebrew family display). This module is the only place that decides:

  - whether to show the Shabbat / holiday strip (and which "mode" it's in)
  - whether to include the Omer count
  - which calendar events are still upcoming
  - whether the device should switch to night mode
  - which weather glyph kind matches the current conditions

All time comparisons are done in Asia/Jerusalem (the displayed timezone).

Schema (subset relevant to the renderer; see ``web/screen.jsx`` for the full
shape):

    {
        "city": str,
        "weekday": str,                 # "יום שני"
        "hebrew_date": str,             # "י׳ באייר תשפ״ו"
        "gregorian_date": str,          # "27.04.2026"
        "time": str,                    # "14:23" (drives greeting + countdown
                                        #          + night mode in screen.jsx)

        "weather_kind": str,            # 'sun'|'cloudy_sun'|'cloudy'|'rainy'|
                                        # 'stormy'|'snow'|'night'|'fog'
        "temp_max": int,
        "temp_min": int,
        "rain_chance": int,             # 0..100

        "all_day_events": list[str],    # titles only
        "timed_events": list[{
            "time": "HH:MM",
            "title": str,
            "is_tomorrow": bool,
        }],

        "omer": {"day": int, "total": 49} | None,

        "shabbat": {                    # only on Fri/Sat or chag windows
            "parsha": str,
            "candle_lighting": "HH:MM",
            "sunset": "HH:MM",
            "havdalah": "HH:MM",
            "mode": "incoming"|"active"|"outgoing",
        } | None,

        "night_mode": bool,             # 00:00 <= hour < 05:00 (Asia/Jerusalem)

        # Metadata, not used by the renderer but kept for downstream tooling.
        "generated_at": ISO datetime,
        "next_update_at": ISO datetime,
        "clock_area": {x, y, width, height},
    }
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

# Night mode window. The design (web/screen.jsx) hard-codes 00:00..05:00 — keep
# this in sync with that file or the firmware will see two different "night
# mode" definitions.
NIGHT_MODE_START_HOUR = 0   # 00:00 (inclusive)
NIGHT_MODE_END_HOUR = 5     # 05:00 (exclusive)

# Display-window rules for the Shabbat / holiday strip
SHABBAT_BOX_THURSDAY_START_HOUR = 6   # Friday Shabbat: visible from Thu 06:00
HOLIDAY_BOX_SAME_DAY_START_HOUR = 12  # Other holidays: visible from candles_day 12:00

CLOCK_AREA = {"x": 520, "y": 0, "width": 280, "height": 120}

OMER_TOTAL = 49


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
        dict matching the schema above. Missing fields are returned as None
        (the renderer handles those gracefully).
    """
    if now is None:
        now = datetime.now(JERUSALEM_TZ)
    elif now.tzinfo is None:
        now = JERUSALEM_TZ.localize(now)
    else:
        now = now.astimezone(JERUSALEM_TZ)

    today_iso = now.date().isoformat()
    today_hebcal = (hebcal.get("by_date", {}) if hebcal else {}).get(today_iso, {})

    weather_dict = _normalize_weather(weather)
    shabbat_dict = _build_shabbat(hebcal, now)

    return {
        # Metadata (not consumed by screen.jsx, kept for logs/debug).
        "generated_at": now.replace(microsecond=0).isoformat(),
        "next_update_at": _next_hour(now).isoformat(),
        "clock_area": CLOCK_AREA,

        # Identity / dates.
        "city": (weather_dict or {}).get("city") or "בית שמש",
        "weekday": today_hebcal.get("weekday_he") or HEBREW_WEEKDAYS[now.weekday()],
        "hebrew_date": today_hebcal.get("hebrew_date"),
        "gregorian_date": now.strftime("%d.%m.%Y"),
        "time": now.strftime("%H:%M"),

        # Weather (flattened — screen.jsx reads them at top level).
        "weather_kind": _derive_weather_kind(weather_dict, now),
        "temp_max": (weather_dict or {}).get("temp_max"),
        "temp_min": (weather_dict or {}).get("temp_min"),
        "rain_chance": (weather_dict or {}).get("rain_chance"),

        # Events.
        "all_day_events": _build_events_all_day(events, now),
        "timed_events": _build_events_timed(events, now),

        # Hebrew calendar.
        "omer": _build_omer(today_hebcal),
        "shabbat": shabbat_dict,
        "night_mode": _is_night_mode(now),
    }


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------


def _normalize_weather(weather: Optional[dict]) -> Optional[dict]:
    """Map the fetcher dict to canonical keys used everywhere downstream."""
    if not weather:
        return None
    return {
        "city": "בית שמש",
        "temp_max": weather.get("temp_max"),
        "temp_min": weather.get("temp_min"),
        "rain_chance": weather.get("precipitation_chance"),
        "sunrise": weather.get("sunrise"),
        "sunset": weather.get("sunset"),
    }


def _derive_weather_kind(weather: Optional[dict], now: datetime) -> str:
    """Pick the closest weather glyph kind for the current conditions.

    The screen has 8 glyphs but we only auto-select among the 5 we can infer
    from temperature + precipitation + sun position. ('snow', 'stormy', 'fog'
    require richer data than Open-Meteo's daily API gives us — they're left
    available as manual overrides if a future fetcher provides them.)
    """
    if not weather:
        return "sun"

    rain = weather.get("rain_chance") or 0
    sunrise = _split_hhmm_or_none(weather.get("sunrise"))
    sunset = _split_hhmm_or_none(weather.get("sunset"))

    is_night = False
    if sunrise and sunset:
        now_minutes = now.hour * 60 + now.minute
        sr_minutes = sunrise[0] * 60 + sunrise[1]
        ss_minutes = sunset[0] * 60 + sunset[1]
        is_night = now_minutes < sr_minutes or now_minutes >= ss_minutes

    if rain >= 60:
        return "rainy"
    if rain >= 30:
        return "cloudy"
    if is_night:
        return "night"
    if rain >= 10:
        return "cloudy_sun"
    return "sun"


# ---------------------------------------------------------------------------
# Shabbat / holiday strip
# ---------------------------------------------------------------------------


def _build_shabbat(hebcal: Optional[dict], now: datetime) -> Optional[dict]:
    """Decide whether to show the Shabbat / holiday strip and build it.

    Window rules:
      - Friday Shabbat: from Thursday 06:00 → that Saturday's havdalah.
      - Other holidays: from candles_day 12:00 → that holiday's havdalah.

    Mode (drives potential future visual states in screen.jsx):
      - "incoming" : current time is before candle lighting.
      - "active"   : between candle lighting and havdalah.
      - "outgoing" : after havdalah but still inside the visibility window
                     (currently we hide the strip at havdalah, so this is
                     reserved — present in the schema for forward compat).
    """
    if not hebcal:
        return None
    by_date = hebcal.get("by_date", {})
    today = now.date()

    # Find the next havdalah at or after today.
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

    # Find the most recent candles on or before that havdalah.
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

    h_h, h_m = _split_hhmm(havdalah_time)
    end = JERUSALEM_TZ.localize(datetime.combine(havdalah_date, dtime(h_h, h_m)))

    if not (start <= now <= end):
        return None

    havdalah_info = by_date.get(havdalah_date.isoformat(), {})
    parsha = _shabbat_strip_title(candles_info, havdalah_info, is_friday_shabbat)

    # Mode: relative to candle lighting on `candles_date`.
    c_h, c_m = _split_hhmm(candles_time)
    candle_dt = JERUSALEM_TZ.localize(datetime.combine(candles_date, dtime(c_h, c_m)))
    if now < candle_dt:
        mode = "incoming"
    elif now < end:
        mode = "active"
    else:
        mode = "outgoing"

    return {
        "parsha": parsha,
        "candle_lighting": candles_time,
        "sunset": _approx_sunset_from_candles(candles_time),
        "havdalah": havdalah_time,
        "mode": mode,
    }


def _shabbat_strip_title(
    candles_info: dict, havdalah_info: dict, is_friday_shabbat: bool
) -> str:
    """Pick the parsha / holiday name for the strip.

    Major holidays override the parasha title. Minor / modern / fast / Rosh
    Chodesh holidays that happen to coincide with Shabbat don't.

    The "פרשת " prefix is stripped — screen.jsx puts the label "פרשת השבוע"
    above the value separately, so passing in "פרשת אמור" would render as
    "פרשת השבוע / פרשת אמור" (redundant).
    """
    parashah = havdalah_info.get("parashah") or candles_info.get("parashah")

    major_holiday = None
    for info in (candles_info, havdalah_info):
        if info.get("holiday") and info.get("holiday_subcat") == "major":
            major_holiday = info["holiday"]
            break

    if major_holiday:
        return major_holiday
    if parashah:
        return _strip_parasha_prefix(parashah)
    fallback_holiday = candles_info.get("holiday") or havdalah_info.get("holiday")
    if fallback_holiday:
        return fallback_holiday
    return "שבת"


def _strip_parasha_prefix(parashah: str) -> str:
    """'פרשת אמור' -> 'אמור'. Leaves non-prefixed names alone."""
    if not parashah:
        return ""
    prefix = "פרשת "
    if parashah.startswith(prefix):
        return parashah[len(prefix):]
    return parashah


def _approx_sunset_from_candles(candles_hhmm: str) -> str:
    """Approximate sunset = candles + 18 minutes (typical Israeli minhag)."""
    h, m = _split_hhmm(candles_hhmm)
    total = h * 60 + m + 18
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------


def _build_events_timed(events: Optional[list[dict]], now: datetime) -> list[dict]:
    """Return upcoming timed events (today + tomorrow), sorted chronologically.

    Output schema: ``{"time": "HH:MM", "title": str, "is_tomorrow": bool}``.
    The renamed "start" → "time" matches what screen.jsx expects.
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
            "time": dt.strftime("%H:%M"),
            "title": title,
            "is_tomorrow": dt.date() > today,
        }
        for dt, title in upcoming
    ]


def _build_events_all_day(events: Optional[list[dict]], now: datetime) -> list[str]:
    """Return all-day event titles whose date is today or tomorrow.

    The new schema is ``list[str]`` (just titles) — screen.jsx shows the
    first one as a bullet line, no need for richer per-event metadata.
    """
    if not events:
        return []
    today = now.date()
    tomorrow = today + timedelta(days=1)
    out: list[str] = []
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
        out.append(ev["title"])
    return out


# ---------------------------------------------------------------------------
# Omer + night mode
# ---------------------------------------------------------------------------


def _build_omer(today_hebcal: dict) -> Optional[dict]:
    """Schema: ``{"day": int, "total": 49}``. The full Hebrew phrase is built
    inside screen.jsx (``buildOmerPhrase``) — we don't pass Hebcal's text here
    because the design wants its own punctuation and the "הרחמן" wish line."""
    day = today_hebcal.get("omer_day")
    if day is None:
        return None
    return {"day": day, "total": OMER_TOTAL}


def _is_night_mode(now: datetime) -> bool:
    h = now.astimezone(JERUSALEM_TZ).hour
    return NIGHT_MODE_START_HOUR <= h < NIGHT_MODE_END_HOUR


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _next_hour(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def _parse_iso_to_jerusalem(value: str) -> datetime:
    """Parse an ISO datetime string to a timezone-aware datetime in Asia/Jerusalem."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = JERUSALEM_TZ.localize(dt)
    return dt.astimezone(JERUSALEM_TZ)


def _split_hhmm(hhmm: str) -> tuple[int, int]:
    h, m = hhmm.split(":")
    return int(h), int(m)


def _split_hhmm_or_none(value) -> Optional[tuple[int, int]]:
    if not isinstance(value, str) or ":" not in value:
        return None
    try:
        return _split_hhmm(value)
    except (ValueError, AttributeError):
        return None


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
    events = None  # Calendar likely None without creds — test resilience

    model = build_data_model(weather, hebcal, events)
    print(json.dumps(model, indent=2, ensure_ascii=False))
