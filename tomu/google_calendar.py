"""Google Calendar: lets the agent read your upcoming events (read-only).

Sign in first with `uv run tomu-google` (see tomu/google_auth.py).
"""

from datetime import UTC, datetime, timedelta

from tomu.google_auth import CALENDAR, google_api
from tomu.tools import Tool


def fetch_events(days: int) -> list[dict]:
    """Events from your primary calendar, from now until `days` from now."""
    now = datetime.now(UTC)
    calendar = google_api("calendar", "v3", CALENDAR, "Google Calendar")
    events, page = [], None
    while True:  # Google sends long calendars a page at a time
        response = calendar.events().list(
            calendarId="primary", timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=days)).isoformat(),
            singleEvents=True, orderBy="startTime", pageToken=page,
        ).execute()
        events += response.get("items", [])
        page = response.get("nextPageToken")
        if not page:
            return events


def describe(event: dict) -> str:
    start = event["start"].get("dateTime") or event["start"].get("date")  # all-day events
    line = f"{start}  {event.get('summary', '(no title)')}"
    return f"{line} @ {event['location']}" if event.get("location") else line


def list_events(days: int = 7) -> str:
    events = fetch_events(days)
    if not events:
        return f"No events in the next {days} day(s)."
    return "\n".join(describe(event) for event in events)


calendar_tool = Tool(
    name="list_calendar_events",
    description="List the user's upcoming Google Calendar events, with start times.",
    input_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "How many days ahead. Default 7."}
        },
    },
    run=list_events,
)
