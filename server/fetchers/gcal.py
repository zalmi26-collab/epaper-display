"""Google Calendar fetcher — events for today + tomorrow.

Auth: Service Account JSON, scope = calendar.readonly.
Calendar must be shared with the service account email (read access).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_ACCOUNT_PATH = "secrets/service_account.json"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def fetch_events(
    calendar_id: str,
    service_account_path: str = DEFAULT_SERVICE_ACCOUNT_PATH,
    now: Optional[datetime] = None,
    days_ahead: int = 2,
) -> Optional[list[dict]]:
    """Fetch upcoming events from a single Google Calendar.

    Args:
        calendar_id: e.g. 'family@group.calendar.google.com'.
        service_account_path: path to JSON key file.
        now: reference time, defaults to UTC now.
        days_ahead: window length (today + tomorrow = 2).

    Returns:
        list of event dicts: {start (ISO str), end (ISO str), title (str), all_day (bool)}.
        Empty list if no events. None on auth/network failure.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    if not Path(service_account_path).exists():
        logger.error("Service account file not found at %s", service_account_path)
        return None

    if now is None:
        now = datetime.now(timezone.utc)

    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=CALENDAR_SCOPES
        )
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
    except (HttpError, FileNotFoundError, ValueError) as e:
        logger.error("Calendar fetch failed: %s", e)
        return None

    events = []
    for item in response.get("items", []):
        parsed = _parse_event(item)
        if parsed is not None:
            events.append(parsed)
    return events


def _parse_event(item: dict) -> Optional[dict]:
    """Normalize a Google Calendar event item to our schema."""
    start_obj = item.get("start", {})
    end_obj = item.get("end", {})
    title = item.get("summary", "(ללא כותרת)").strip()

    # All-day events use "date"; timed events use "dateTime".
    if "date" in start_obj:
        return {
            "start": start_obj["date"],
            "end": end_obj.get("date", start_obj["date"]),
            "title": title,
            "all_day": True,
        }
    if "dateTime" in start_obj:
        return {
            "start": start_obj["dateTime"],
            "end": end_obj.get("dateTime", start_obj["dateTime"]),
            "title": title,
            "all_day": False,
        }
    return None


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    calendar_id = os.environ.get("CALENDAR_ID")
    if not calendar_id:
        print("CALENDAR_ID env var not set — set it to test. Example:")
        print("  export CALENDAR_ID='your-calendar-id@group.calendar.google.com'")
        print("(also requires secrets/service_account.json)")
    else:
        result = fetch_events(calendar_id)
        if result is None:
            print("FAILED — see logs above")
        else:
            print(f"Found {len(result)} events:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
