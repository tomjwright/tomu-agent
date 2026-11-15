import base64
import json

import pytest

from tomu import gmail
from tomu.google_auth import CALENDAR
from tomu.tools import ToolRegistry


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


EMAIL = {
    "id": "abc",
    "snippet": "See you at 10",
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [{"name": "From", "value": "Sarah <sarah@example.com>"},
                    {"name": "Subject", "value": "Lunch"},
                    {"name": "Date", "value": "Mon, 16 Nov 2026 09:00:00 +0800"}],
        "parts": [{"mimeType": "text/html", "body": {"data": encoded("<p>See you</p>")}},
                  {"mimeType": "text/plain", "body": {"data": encoded("See you at 10.")}}],
    },
}


def test_an_email_is_described_by_its_id_date_sender_and_subject():
    assert gmail.describe(EMAIL) == (
        "id abc | Mon, 16 Nov 2026 09:00:00 +0800 | Sarah <sarah@example.com>\n"
        "Lunch: See you at 10"
    )


def test_the_plain_text_body_is_found_inside_a_multipart_email():
    assert gmail.plain_text(EMAIL["payload"]) == "See you at 10."


def test_a_calendar_only_sign_in_asks_you_to_sign_in_again_for_gmail(tmp_path, monkeypatch):
    pytest.importorskip("google.oauth2")
    token = tmp_path / "token.json"
    token.write_text(json.dumps({"client_id": "id", "client_secret": "secret",
                                 "refresh_token": "refresh", "scopes": [CALENDAR]}))
    monkeypatch.setenv("TOMU_GOOGLE_TOKEN", str(token))

    output, is_error = ToolRegistry([gmail.search_email_tool]).execute(
        "search_email", {"query": "is:unread"})

    assert is_error
    assert "Gmail isn't connected yet" in output
