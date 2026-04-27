"""Unit tests for server/builder.py."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
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


class ShabbatBoxTests(unittest.TestCase):
    def test_hidden_on_sunday(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 3, 10))
        self.assertIsNone(m["shabbat_box"])

    def test_hidden_on_wednesday(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 29, 12))
        self.assertIsNone(m["shabbat_box"])

    def test_hidden_thursday_before_06_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 5, 30))
        self.assertIsNone(m["shabbat_box"])

    def test_visible_thursday_06_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 6, 0))
        self.assertIsNotNone(m["shabbat_box"])
        self.assertEqual(m["shabbat_box"]["title"], "פרשת אמור")
        self.assertFalse(m["shabbat_box"]["is_holiday"])

    def test_visible_friday_evening(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 1, 19, 30))
        self.assertEqual(m["shabbat_box"]["title"], "פרשת אמור")

    def test_visible_saturday_before_havdalah(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 2, 19, 0))
        self.assertEqual(m["shabbat_box"]["title"], "פרשת אמור")

    def test_hidden_saturday_after_havdalah(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 5, 2, 21, 0))
        self.assertIsNone(m["shabbat_box"])

    def test_minor_holiday_does_not_replace_parasha_title(self):
        # Pesach Sheni (May 1, subcat=minor) coincides with the Shabbat eve;
        # the box should still read "פרשת אמור".
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 30, 8, 0))
        self.assertEqual(m["shabbat_box"]["title"], "פרשת אמור")


class NightModeTests(unittest.TestCase):
    def test_off_at_evening_22(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 22, 59))
        self.assertFalse(m["night_mode"])

    def test_on_at_23_00(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 23, 0))
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
        timed_titles = [ev["title"] for ev in m["events_timed"]]
        self.assertEqual(timed_titles, ["future meeting"])

    def test_tomorrow_flag_set_for_next_day_events(self):
        events = [
            {"start": "2026-04-28T09:00:00+03:00", "end": "2026-04-28T10:00:00+03:00",
             "title": "tomorrow only", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(len(m["events_timed"]), 1)
        self.assertTrue(m["events_timed"][0]["is_tomorrow"])

    def test_chronological_order_today_then_tomorrow(self):
        events = [
            {"start": "2026-04-28T09:00:00+03:00", "end": "2026-04-28T10:00:00+03:00",
             "title": "tomorrow", "all_day": False},
            {"start": "2026-04-27T22:30:00+03:00", "end": "2026-04-27T23:30:00+03:00",
             "title": "today", "all_day": False},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        order = [(ev["start"], ev["title"]) for ev in m["events_timed"]]
        self.assertEqual(order, [("22:30", "today"), ("09:00", "tomorrow")])

    def test_all_day_event_visible_today(self):
        events = [
            {"start": "2026-04-27", "end": "2026-04-28",
             "title": "birthday", "all_day": True},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual([e["title"] for e in m["events_all_day"]], ["birthday"])

    def test_all_day_event_yesterday_hidden(self):
        events = [
            {"start": "2026-04-26", "end": "2026-04-27",
             "title": "yesterday", "all_day": True},
        ]
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, events,
                             jerusalem(2026, 4, 27, 14, 0))
        self.assertEqual(m["events_all_day"], [])


class GracefulDegradationTests(unittest.TestCase):
    def test_no_weather(self):
        m = build_data_model(None, HEBCAL_FIXTURE, [], jerusalem(2026, 4, 27, 14))
        self.assertIsNone(m["weather"])
        # Other fields should still be populated
        self.assertEqual(m["date"]["gregorian"], "27.04.2026")

    def test_no_hebcal(self):
        m = build_data_model(WEATHER_FIXTURE, None, [], jerusalem(2026, 4, 27, 14))
        self.assertIsNone(m["shabbat_box"])
        self.assertIsNone(m["omer"])
        # Date still computed from "now"
        self.assertEqual(m["date"]["gregorian"], "27.04.2026")
        self.assertIsNone(m["date"]["hebrew"])

    def test_no_events(self):
        m = build_data_model(WEATHER_FIXTURE, HEBCAL_FIXTURE, None,
                             jerusalem(2026, 4, 27, 14))
        self.assertEqual(m["events_timed"], [])
        self.assertEqual(m["events_all_day"], [])


if __name__ == "__main__":
    unittest.main()
