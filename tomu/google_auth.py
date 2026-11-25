"""Signing in to Google, shared by the Calendar and Gmail tools.

Run `uv run tomu-google` once: it opens your browser to sign in to Google and
saves the login token on your machine (google-token.json, or TOMU_GOOGLE_TOKEN).
It needs a Google OAuth "Desktop app" client, set as GOOGLE_CLIENT_ID and
GOOGLE_CLIENT_SECRET in .env, and the optional Google libraries:
`uv sync --extra google`. It asks to read your calendar and email, add events
and send email; the agent only adds or sends after you approve each one.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

CALENDAR = "https://www.googleapis.com/auth/calendar.events.readonly"
CALENDAR_WRITE = "https://www.googleapis.com/auth/calendar.events"
GMAIL = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
NOT_INSTALLED = "Google support isn't installed. Run: uv sync --extra google"


def token_path() -> Path:
    return Path(os.getenv("TOMU_GOOGLE_TOKEN", "google-token.json"))


def save_token(credentials) -> None:
    # created readable by only you, since the token opens your account
    file = os.open(token_path(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(file, 0o600)  # also tightens a token file that already existed
    with os.fdopen(file, "w") as token:
        token.write(credentials.to_json())


def connect() -> None:
    """`uv run tomu-google`: sign in to Google in the browser and save the token."""
    load_dotenv()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit(NOT_INSTALLED) from None
    client = {
        "installed": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client, [CALENDAR, CALENDAR_WRITE, GMAIL, GMAIL_SEND]
    )
    save_token(flow.run_local_server(port=0))
    print(f"Connected. Token saved to {token_path()}")


def google_api(name: str, version: str, scope: str, label: str):
    """A client for one Google API, e.g. google_api("gmail", "v1", GMAIL, "Gmail")."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(NOT_INSTALLED) from None
    not_connected = f"{label} isn't connected yet. Run: uv run tomu-google"
    if not token_path().exists():
        raise RuntimeError(not_connected)

    credentials = Credentials.from_authorized_user_file(str(token_path()))
    if not credentials.has_scopes([scope]):  # signed in before this tool existed
        raise RuntimeError(not_connected)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())  # the login lasts; the access token is short-lived
        save_token(credentials)
    return build(name, version, credentials=credentials, cache_discovery=False)
