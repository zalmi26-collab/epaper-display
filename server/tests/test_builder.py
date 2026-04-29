"""Unit tests for server/builder.py."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

import pytz

# Make `server` importable when running `python -m unittest` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from builder import build_data_model  # noqa: E402

JERUSALEM_TZ = pytz.timezone("Asia/Jerusalem")


def jerusalem(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return JERUSALEM_TZ.localize(datetime(year, month, day, hour, minute))


# Synthetic Hebcal payload for the week 2026-04-27 .. 2026-05-04
HEBCAL_FIXTURE = {
    "by_date": {
        "2026-04-27": {
            "hebrew_date": "י׳ אייר תשפ״ו",
            "weekday_he": "יום שני",
            "parashah": None, "holiday": "יום הרצל", "holiday_subcat": "modern",
            "candles": None, "havdalah": None,
            "omer_day": 25, "omer_text": "היום עשרים וחמישה ימים לעומר",
        },
        "2026-04-30": {
            "hebrew_date": "י״ג אייר תשפ״ו",
            "weekday_he": "יום חמישי",
            "parashah": None, "holiday": None, "holiday_subcat": None,
            "candles": None, "havdalah": None,
            "omer_day": 28, "omer_text": "היום עשרים ושמונה ימים לעומר",
        },
        "2026-05-01": {
            "hebrew_date": "י״ד אייר תשפ״ו",
            "weekday_he": "יום שישי",
            "parashah": None, "holiday": "פסח שני", "holiday_subcat": "minor",
            "candles": "19:02", "havdalah": None,
            "omer_day": 29, "omer_text": "היום עשרים ותשעה ימים לעומר",
        },
        "2026-05-02": {
            "hebrew_date": "ט״ו אייר תשפ״ו",
            "weekday_he": "שבת",
            "parashah": "פרשת אמור", "holiday": None, "holiday_subcat": None,
            "candles": None, "havdalah": "20:01",
            "omer_day": 30, "omer_text": "היום שלשים ימים לעומר",
        },
        "2026-05-03": {
            "hebrew_date": "ט״ז אייר תשפ״ו",
            "weekday_he": "יום ראשון",
            "parashah": None, "holiday": None, "holiday_subcat": None,
            "candles": None, "havdalah": None,
            "omer_day": 31, "omer_text": "היום שלשים ואחד ימים לעומר",
        },
    }
}

WEATHER_FIXTURE = {
    "temp_max": 23, "temp_min": 13, "precipitation_chance": 60,
    "sunrise": "05:58", "sunset": "19:16",
}


class ShabbatStripTests(unittest.TestCase):
    """The Shabbat strip is the renamed shabbat_box — same logic, new schema."""

    def test_hidden_on_sunday(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 3, 10))
        self.assertIsNone(m["shabbat"])

    def test_hidden_on_wednesday(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 29, 12))
        self.assertIsNone(m["shabbat"])

    def test_hidden_thursday_before_06_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 5, 30))
        self.assertIsNone(m["shabbat"])

    def test_visible_thursday_06_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 6, 0))
        self.assertIsNotNone(m["shabbat"])
        self.assertEqual(m["shabbat"]["parsha"], "אמור")
        self.assertEqual(m["shabbat"]["mode"], "incoming")
        self.assertEqual(m["shabbat"]["candle_lighting"], "19:02")

    def test_visible_friday_evening(self):
        # Friday 19:30 — past candle lighting, should be 'active'.
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 1, 19, 30))
        self.assertEqual(m["shabbat"]["parsha"], "אמור")
        self.assertEqual(m["shabbat"]["mode"], "active")

    def test_visible_saturday_before_havdalah(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 2, 19, 0))
        self.assertEqual(m["shabbat"]["parsha"], "אמור")
        self.assertEqual(m["shabbat"]["mode"], "active")

    def test_hidden_saturday_after_havdalah(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 2, 21, 0))
        self.assertIsNone(m["shabbat"])

    def test_minor_holiday_does_not_replace_parasha_title(self):
        # Pesach Sheni (May 1, subcat=minor) coincides with the Shabbat eve;
        # the strip should still read the parsha name (without "פרשת " prefix).
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 8, 0))
        self.assertEqual(m["shabbat"]["parsha"], "אמור")

    def test_parsha_prefix_is_stripped(self):
        # Hebcal returns "פרשת אמור"; the strip's parsha field should hold the
        # bare word so screen.jsx's "פרשת השבוע" label doesn't double up.
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 2, 10))
        self.assertEqual(m["shabbat"]["parsha"], "אמור")


class NightModeTests(unittest.TestCase):
    """Night mode is now 00:00..05:00 (was 23:00..05:00 in the previous design)."""

    def test_off_at_22_59(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 22, 59))
        self.assertFalse(m["night_mode"])

    def test_off_at_23_00(self):
        # 23:00 was night-mode under the old design; new design defers to 00:00.
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 23, 0))
        self.assertFalse(m["night_mode"])

    def test_on_at_00_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 28, 0, 0))
        self.assertTrue(m["night_mode"])

    def test_on_at_04_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 28, 4, 0))
        self.assertTrue(m["night_mode"])

    def test_off_at_05_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 28, 5, 0))
        self.assertFalse(m["night_mode"])


class OmerTests(unittest.TestCase):
    def test_present_during_counting(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 12))
        self.assertIsNotNone(m["omer"])
        self.assertEqual(m["omer"]["day"], 25)
        self.assertEqual(m["omer"]["total"], 49)
        # Hebcal's pre-formatted omer text is no longer passed through —
        # screen.jsx (buildOmerPhrase) renders the full Hebrew sentence itself.
        self.assertNotIn("text", m["omer"])


class EventsTests(unittest.TestCase):
    def test_only_future_timed_events(self):
        events = [
            {"start": "2026-04-27T10:00:00+03:00", "end": "2026-04-27T11:00:00+03:00",
             "title": "past meeting", "all_day": False},
            {"start": "2026-04-27T18:00:00+03:00", "end": "2026-04-27T19:00:00+03:00",
             "title": "future meeting", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        timed_titles = [ev["title"] for ev in m["timed_events"]]
        self.assertEqual(timed_titles, ["future meeting"])

    def test_timed_event_has_time_field_not_start(self):
        # screen.jsx reads `time`, not `start`. Make sure the rename stuck.
        events = [
            {"start": "2026-04-27T18:00:00+03:00", "end": "2026-04-27T19:00:00+03:00",
             "title": "tonight", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(m["timed_events"][0]["time"], "18:00")
        self.assertNotIn("start", m["timed_events"][0])

    def test_tomorrow_flag_set_for_next_day_events(self):
        events = [
            {"start": "2026-04-28T09:00:00+03:00", "end": "2026-04-28T10:00:00+03:00",
             "title": "tomorrow only", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(len(m["timed_events"]), 1)
        self.assertTrue(m["timed_events"][0]["is_tomorrow"])

    def test_chronological_order_today_then_tomorrow(self):
        events = [
            {"start": "2026-04-28T09:00:00+03:00", "end": "2026-04-28T10:00:00+03:00",
             "title": "tomorrow", "all_day": False},
            {"start": "2026-04-27T22:30:00+03:00", "end": "2026-04-27T23:30:00+03:00",
             "title": "today", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        order = [(ev["time"], ev["title"]) for ev in m["timed_events"]]
        self.assertEqual(order, [("22:30", "today"), ("09:00", "tomorrow")])

    def test_all_day_event_visible_today_as_string(self):
        # New schema: all_day_events is list[str], not list[{"title": str}].
        events = [
            {"start": "2026-04-27", "end": "2026-04-28",
             "title": "birthday", "all_day": True},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(m["all_day_events"], ["birthday"])

    def test_all_day_event_yesterday_hidden(self):
        events = [
            {"start": "2026-04-26", "end": "2026-04-27",
             "title": "yesterday", "all_day": True},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(m["all_day_events"], [])


class WeatherKindTests(unittest.TestCase):
    """The weather_kind field is derived server-side and picks one of the 8
    glyphs the design supports. Verify the inference matches expectations."""

    def _kind(self, *, rain: int, hour: int, sunrise="05:58", sunset="19:16") -> str:
        weather = {
            "temp_max": 24, "temp_min": 14,
            "precipitation_chance": rain,
            "sunrise": sunrise, "sunset": sunset,
        }
        m = build_data_model(weather, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, hour))
        return m["weather_kind"]

    def test_clear_day_is_sun(self):
        self.assertEqual(self._kind(rain=0, hour=12), "sun")

    def test_light_rain_with_sun(self):
        self.assertEqual(self._kind(rain=20, hour=12), "cloudy_sun")

    def test_moderate_clouds(self):
        self.assertEqual(self._kind(rain=40, hour=12), "cloudy")

    def test_heavy_rain(self):
        self.assertEqual(self._kind(rain=70, hour=12), "rainy")

    def test_after_sunset_is_night(self):
        self.assertEqual(self._kind(rain=0, hour=21), "night")

    def test_before_sunrise_is_night(self):
        self.assertEqual(self._kind(rain=0, hour=4), "night")


class FlatSchemaTests(unittest.TestCase):
    """The new schema flattens identity / weather to top-level fields, and
    renames a few keys so screen.jsx can read them without adapter code."""

    def test_top_level_identity(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 14))
        self.assertEqual(m["weekday"], "יום שני")
        self.assertEqual(m["hebrew_date"], "י׳ אייר תשפ״ו")
        self.assertEqual(m["gregorian_date"], "27.04.2026")
        self.assertEqual(m["time"], "14:00")
        self.assertEqual(m["city"], "בית שמש")

    def test_top_level_weather(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 14))
        self.assertEqual(m["temp_max"], 23)
        self.assertEqual(m["temp_min"], 13)
        self.assertEqual(m["rain_chance"], 60)


class GracefulDegradationTests(unittest.TestCase):
    def test_no_weather(self):
        m = build_data_model(None, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 14))
        # Without weather, temps are None and weather_kind falls back to 'sun'.
        self.assertIsNone(m["temp_max"])
        self.assertIsNone(m["temp_min"])
        self.assertIsNone(m["rain_chance"])
        self.assertEqual(m["weather_kind"], "sun")
        # Date still computed from "now"
        self.assertEqual(m["gregorian_date"], "27.04.2026")
        # City has a sane default even without weather.
        self.assertEqual(m["city"], "בית שמש")

    def test_no_hebcal(self):
        m = build_data_model(WEATHER_FIXTURE, None, [], jerusalem(2026, 4, 27, 14))
        self.assertIsNone(m["shabbat"])
        self.assertIsNone(m["omer"])
        self.assertEqual(m["gregorian_date"], "27.04.2026")
        self.assertIsNone(m["hebrew_date"])
        # Weekday falls back to Python's calendar when Hebcal didn't supply it.
        self.assertEqual(m["weekday"], "יום שני")

    def test_no_events(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, None,
                             jerusalem(2026, 4, 27, 14))
        self.assertEqual(m["timed_events"], [])
        self.assertEqual(m["all_day_events"], [])


if __name__ == "__main__":
    unittest.main()
