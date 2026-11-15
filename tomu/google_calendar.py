"""Google Calendar: lets the agent read your upcoming events (read-only).

Connect once with `uv run tomu-google`: it opens your browser to sign in to
Google and saves the login token on your machine (google-token.json, or
TOMU_GOOGLE_TOKEN). It needs a Google OAuth "Desktop app" client, set as
GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, and the optional Google
libraries: `uv sync --extra google`.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from tomu.tools import Tool

SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
NOT_INSTALLED = "Google support isn't installed. Run: uv sync --extra google"
NOT_CONNECTED = "Google Calendar isn't connected yet. Run: uv run tomu-google"


def token_path() -> Path:
    return Path(os.getenv("TOMU_GOOGLE_TOKEN", "google-token.json"))


def save_token(credentials) -> None:
    # created readable by only you, since the token opens your calendar
    file = os.open(token_path(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(file, "w") as token:
        token.write(credentials.to_json())


def connect() -> None:
    """`uv run tomu-google`: sign in to Google in the browser and save the token."""
    load_dotenv()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit(NOT_INSTALLED) from None
    client = {"installed": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }}
    save_token(InstalledAppFlow.from_client_config(client, SCOPES).run_local_server(port=0))
    print(f"Connected. Token saved to {token_path()}")


def fetch_events(days: int) -> list[dict]:
    """Events from your primary calendar, from now until `days` from now."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(NOT_INSTALLED) from None
    if not token_path().exists():
        raise RuntimeError(NOT_CONNECTED)

    credentials = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())  # the login lasts; the access token is short-lived
        save_token(credentials)

    now = datetime.now(UTC)
    calendar = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    response = calendar.events().list(
        calendarId="primary", timeMin=now.isoformat(),
        timeMax=(now + timedelta(days=days)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    return response.get("items", [])


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
