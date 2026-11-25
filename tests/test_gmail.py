import base64
import json
from types import SimpleNamespace as Obj

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
        "headers": [
            {"name": "From", "value": "Sarah <sarah@example.com>"},
            {"name": "Subject", "value": "Lunch"},
            {"name": "Date", "value": "Mon, 16 Nov 2026 09:00:00 +0800"},
        ],
        "parts": [
            {"mimeType": "text/html", "body": {"data": encoded("<p>See you</p>")}},
            {"mimeType": "text/plain", "body": {"data": encoded("See you at 10.")}},
        ],
    },
}


def test_an_email_is_described_by_its_id_date_sender_and_subject():
    assert gmail.describe(EMAIL) == (
        "id abc | Mon, 16 Nov 2026 09:00:00 +0800 | Sarah <sarah@example.com>\nLunch: See you at 10"
    )


def test_the_plain_text_body_is_found_inside_a_multipart_email():
    assert gmail.plain_text(EMAIL["payload"]) == "See you at 10."


def test_a_calendar_only_sign_in_asks_you_to_sign_in_again_for_gmail(tmp_path, monkeypatch):
    pytest.importorskip("google.oauth2")
    token = tmp_path / "token.json"
    token.write_text(
        json.dumps(
            {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "refresh",
                "scopes": [CALENDAR],
            }
        )
    )
    monkeypatch.setenv("TOMU_GOOGLE_TOKEN", str(token))

    output, is_error = ToolRegistry([gmail.search_email_tool]).execute(
        "search_email", {"query": "is:unread"}
    )

    assert is_error
    assert "Gmail isn't connected yet" in output


def test_header_names_are_matched_whatever_their_case():
    email = {
        "id": "x",
        "payload": {
            "headers": [
                {"name": "from", "value": "bob@example.com"},
                {"name": "SUBJECT", "value": "Hi"},
            ]
        },
    }
    assert gmail.describe(email) == "id x |  | bob@example.com\nHi: "


def test_a_body_is_decoded_with_its_own_charset():
    part = {
        "mimeType": "text/plain",
        "headers": [{"name": "Content-Type", "value": 'text/plain; charset="iso-8859-1"'}],
        "body": {"data": base64.urlsafe_b64encode("Café".encode("iso-8859-1")).decode()},
    }
    assert gmail.plain_text(part) == "Café"


def test_an_attached_text_file_is_not_mistaken_for_the_body():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {"mimeType": "text/plain", "filename": "notes.txt", "body": {"data": encoded("notes")}},
            {"mimeType": "text/plain", "filename": "", "body": {"data": encoded("The message.")}},
        ],
    }
    assert gmail.plain_text(payload) == "The message."


def test_send_email_sends_a_plain_text_email(monkeypatch):
    sent = []

    class Messages:
        def send(self, userId, body):
            sent.append(body)
            return Obj(execute=lambda: {"id": "m1"})

    api = Obj(users=lambda: Obj(messages=Messages))
    monkeypatch.setattr(gmail, "google_api", lambda *args: api)

    output = gmail.send_email("bob@example.com", "Hi", "Hello Bob")

    assert output == "Sent to bob@example.com (id m1)."
    email = base64.urlsafe_b64decode(sent[0]["raw"]).decode()
    assert "To: bob@example.com" in email and "Subject: Hi" in email and "Hello Bob" in email


def test_only_sending_needs_approval():
    assert gmail.send_email_tool.needs_approval
    assert not gmail.search_email_tool.needs_approval and not gmail.read_email_tool.needs_approval
