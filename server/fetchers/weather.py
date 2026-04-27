"""Weather fetcher — Open-Meteo API for Bet Shemesh.

Returns today's max/min temperature, precipitation chance, sunrise, sunset.
No API key needed. Free for non-commercial use.

API docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 31.7497
LONGITUDE = 34.9886
TIMEZONE = "Asia/Jerusalem"
TIMEOUT_SECONDS = 15


def fetch_weather() -> Optional[dict]:
    """Fetch today's weather forecast for Bet Shemesh.

    Returns:
        dict with keys: temp_max (int, °C), temp_min (int, °C),
        precipitation_chance (int, %), sunrise (str, "HH:MM"), sunset (str, "HH:MM").
        None on any failure (network, parsing, malformed response).
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "timezone": TIMEZONE,
        "forecast_days": 2,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Weather fetch failed: %s", e)
        return None

    try:
        daily = data["daily"]
        return {
            "temp_max": round(daily["temperature_2m_max"][0]),
            "temp_min": round(daily["temperature_2m_min"][0]),
            "precipitation_chance": int(daily["precipitation_probability_max"][0] or 0),
            "sunrise": _extract_time(daily["sunrise"][0]),
            "sunset": _extract_time(daily["sunset"][0]),
        }
    except (KeyError, IndexError, TypeError) as e:
        logger.error("Weather parsing failed: %s — raw: %s", e, data)
        return None


def _extract_time(iso_datetime: str) -> str:
    """Extract HH:MM from an ISO datetime string like '2026-04-27T05:48'."""
    return iso_datetime.split("T", 1)[1][:5]


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = fetch_weather()
    print(json.dumps(result, indent=2, ensure_ascii=False))
