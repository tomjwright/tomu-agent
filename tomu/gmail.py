"""Gmail: lets the agent search and read your email (read-only).

Sign in first with `uv run tomu-google` (see tomu/google_auth.py). Sending
email waits for the approval flow, so the agent can't send anything yet.
"""

import base64
import re

from tomu.google_auth import GMAIL, google_api
from tomu.tools import Tool

LONGEST_EMAIL = 4000  # characters of an email body handed to the model


def gmail():
    return google_api("gmail", "v1", GMAIL, "Gmail").users().messages()


def search_email(query: str, max_results: int = 10) -> str:
    messages = gmail()
    found = messages.list(userId="me", q=query, maxResults=max_results).execute()
    emails = [
        messages.get(userId="me", id=item["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
        for item in found.get("messages", [])
    ]
    if not emails:
        return f"No emails match {query!r}."
    return "\n\n".join(describe(email) for email in emails)


def describe(email: dict) -> str:
    headers = header_values(email["payload"])
    return (f"id {email['id']} | {headers.get('date', '')} | {headers.get('from', '')}\n"
            f"{headers.get('subject', '(no subject)')}: {email.get('snippet', '')}")


def header_values(part: dict) -> dict:
    # header names aren't case-sensitive: "From" and "from" are the same header
    return {h["name"].lower(): h["value"] for h in part.get("headers", [])}


def plain_text(part: dict) -> str:
    """The text/plain body of an email, looking inside multipart sections."""
    if part.get("filename"):  # an attached file, not the message itself
        return ""
    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
        content_type = header_values(part).get("content-type", "")
        charset = re.search(r'charset="?([\w.:-]+)', content_type, re.IGNORECASE)
        data = base64.urlsafe_b64decode(part["body"]["data"])
        try:
            return data.decode(charset.group(1) if charset else "utf-8", "replace")
        except LookupError:  # a charset Python doesn't know
            return data.decode("utf-8", "replace")
    return next((text for sub in part.get("parts", []) if (text := plain_text(sub))), "")


def read_email(id: str) -> str:
    email = gmail().get(userId="me", id=id, format="full").execute()
    body = plain_text(email["payload"]) or email.get("snippet", "")
    return f"{describe(email)}\n\n{body[:LONGEST_EMAIL]}"


search_email_tool = Tool(
    name="search_email",
    description=("Search the user's Gmail. Takes a Gmail search query such as "
                 "'from:alice newer_than:7d' or 'is:unread'. Returns ids, senders, "
                 "subjects and snippets."),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A Gmail search query."},
            "max_results": {"type": "integer", "description": "Default 10."},
        },
        "required": ["query"],
    },
    run=search_email,
)

read_email_tool = Tool(
    name="read_email",
    description="Read the full text of one email, by the id search_email returned.",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string", "description": "The email's id."}},
        "required": ["id"],
    },
    run=read_email,
)
