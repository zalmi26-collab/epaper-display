"""Hebcal fetcher — Hebrew dates, parashot, holidays, candle lighting, omer.

Pulls 8 days starting today, parses the items[] array into a per-date dict.
No API key needed. Free.

API docs: https://www.hebcal.com/home/195/jewish-calendar-rest-api
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_URL = "https://www.hebcal.com/hebcal"
CONVERTER_URL = "https://www.hebcal.com/converter"
GEONAME_ID_BET_SHEMESH = 295089
TIMEOUT_SECONDS = 20

# Hebrew weekday names by Python's weekday() (Mon=0 .. Sun=6)
HEBREW_WEEKDAYS = {
    0: "יום שני",
    1: "יום שלישי",
    2: "יום רביעי",
    3: "יום חמישי",
    4: "יום שישי",
    5: "שבת",
    6: "יום ראשון",
}


def fetch_hebcal(start: date, days: int = 8) -> Optional[dict]:
    """Fetch Hebrew calendar data for a date range.

    Args:
        start: First date to include.
        days: Number of days to fetch (inclusive of start).

    Returns:
        dict {"by_date": {YYYY-MM-DD: {...}}, "items_raw": [...]} or None on failure.

        Each per-date dict has fields (any may be None):
            hebrew_date: Hebrew date string e.g. 'כ"ז ניסן תשפ"ו'
            weekday_he: Hebrew weekday e.g. 'יום שני'
            parashah: parasha title in Hebrew (only on Shabbat) e.g. 'פרשת אמור'
            holiday: holiday name in Hebrew, or None
            holiday_subcat: 'major' | 'minor' | 'modern' | 'fast' | None
            candles: 'HH:MM' candle-lighting time on this date, or None
            havdalah: 'HH:MM' havdalah time on this date, or None
            omer_day: int (1..49) or None
            omer_text: Hebrew omer count text, or None
    """
    end = start + timedelta(days=days - 1)
    params = {
        "cfg": "json",
        "v": "1",
        "maj": "on",      # major holidays
        "min": "on",      # minor holidays
        "mod": "on",      # modern holidays (Yom Ha'atzmaut etc.)
        "nx": "on",       # Rosh Chodesh
        "mf": "on",       # minor fasts
        "ss": "on",       # special Shabbatot
        "s": "on",        # weekly parasha
        "c": "on",        # candle lighting
        "o": "on",        # omer
        "d": "on",        # Hebrew date every day (hebdate items)
        "geonameid": GEONAME_ID_BET_SHEMESH,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "lg": "h",
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Hebcal fetch failed: %s", e)
        return None

    items = data.get("items", [])
    if not isinstance(items, list):
        logger.error("Hebcal response missing items[] array")
        return None

    by_date: dict[str, dict] = {}
    cursor = start
    while cursor <= end:
        by_date[cursor.isoformat()] = {
            "hebrew_date": None,
            "weekday_he": HEBREW_WEEKDAYS[cursor.weekday()],
            "parashah": None,
            "holiday": None,
            "holiday_subcat": None,
            "candles": None,
            "havdalah": None,
            "omer_day": None,
            "omer_text": None,
        }
        cursor += timedelta(days=1)

    for item in items:
        date_key = _date_key(item.get("date"))
        if date_key not in by_date:
            continue
        slot = by_date[date_key]
        category = item.get("category")
        title = item.get("title") or item.get("hebrew")

        if category == "hebdate":
            slot["hebrew_date"] = item.get("hebrew") or title
        elif category == "parashat":
            slot["parashah"] = item.get("hebrew") or title
        elif category == "holiday":
            slot["holiday"] = item.get("hebrew") or title
            slot["holiday_subcat"] = item.get("subcat")
        elif category == "candles":
            slot["candles"] = _extract_time(item.get("date"))
        elif category == "havdalah":
            slot["havdalah"] = _extract_time(item.get("date"))
        elif category == "omer":
            # Hebcal returns: omer = {"count": {"he": "...", "en": "..."}, "sefira": {...}}
            # The integer day is parsed from title_orig like "24th day of the Omer".
            slot["omer_day"] = _parse_omer_day(item)
            omer_obj = item.get("omer")
            if isinstance(omer_obj, dict):
                count_obj = omer_obj.get("count")
                if isinstance(count_obj, dict):
                    slot["omer_text"] = count_obj.get("he")
            if slot["omer_text"] is None:
                slot["omer_text"] = item.get("hebrew") or title
        elif category == "roshchodesh":
            # Optional — record as holiday-like info if no major holiday set
            if slot["holiday"] is None:
                slot["holiday"] = item.get("hebrew") or title
                slot["holiday_subcat"] = "roshchodesh"
        elif category == "fast":
            if slot["holiday"] is None:
                slot["holiday"] = item.get("hebrew") or title
                slot["holiday_subcat"] = "fast"

    # The main API's hebdate items omit the Hebrew year — fetch it once from
    # the converter API and append "<day> <month> <year>" to each entry.
    hebrew_year = _fetch_hebrew_year(start)
    if hebrew_year:
        for slot in by_date.values():
            if slot["hebrew_date"]:
                slot["hebrew_date"] = f"{slot['hebrew_date']} {hebrew_year}"

    return {"by_date": by_date, "items_raw": items}


def _fetch_hebrew_year(g_date: date) -> Optional[str]:
    """Fetch Hebrew year string (e.g. 'תשפ״ו') for a Gregorian date.

    Hebrew years rarely change inside an 8-day window — we only need one call.
    """
    params = {
        "cfg": "json",
        "gy": g_date.year,
        "gm": g_date.month,
        "gd": g_date.day,
        "g2h": 1,
        "strict": 1,
    }
    try:
        response = requests.get(CONVERTER_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Hebrew year converter call failed: %s", e)
        return None

    # payload['hebrew'] looks like 'י׳ באייר תשפ״ו' — keep the last token.
    full = payload.get("hebrew")
    if not isinstance(full, str):
        return None
    parts = full.split()
    return parts[-1] if parts else None


def _date_key(value) -> Optional[str]:
    """Extract YYYY-MM-DD portion from a Hebcal date string (date or datetime)."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    return value[:10]


def _extract_time(iso_datetime: Optional[str]) -> Optional[str]:
    """Extract HH:MM from '2026-05-01T18:54:00+03:00' style strings."""
    if not isinstance(iso_datetime, str) or "T" not in iso_datetime:
        return None
    return iso_datetime.split("T", 1)[1][:5]


def _parse_omer_day(item: dict) -> Optional[int]:
    """Extract the numerical omer day from title_orig or title.

    title_orig is always English (e.g. '24th day of the Omer'); Hebrew title
    (with lg=h) looks like 'עומר יום 24'. Both contain the digit run.
    """
    for source in (item.get("title_orig"), item.get("title"), item.get("hebrew")):
        if not isinstance(source, str):
            continue
        for token in source.split():
            digits = "".join(c for c in token if c.isdigit())
            if digits:
                try:
                    value = int(digits)
                    if 1 <= value <= 49:
                        return value
                except ValueError:
                    pass
    return None


if __name__ == "__main__":
    import json
    from datetime import date as _date
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = fetch_hebcal(_date.today(), days=8)
    if result is None:
        print("FAILED")
    else:
        print(json.dumps(result["by_date"], indent=2, ensure_ascii=False))
