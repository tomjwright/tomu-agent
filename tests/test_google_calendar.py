from types import SimpleNamespace as Obj

from tomu import google_calendar
from tomu.tools import ToolRegistry


def test_events_are_listed_one_per_line(monkeypatch):
    monkeypatch.setattr(google_calendar, "fetch_events", lambda days: [
        {"summary": "Standup", "start": {"dateTime": "2026-11-16T09:00:00+08:00"}},
        {"summary": "Holiday", "start": {"date": "2026-11-20"}, "location": "Bali"},
    ])

    assert google_calendar.list_events() == (
        "2026-11-16T09:00:00+08:00  Standup\n"
        "2026-11-20  Holiday @ Bali"
    )


def test_an_unconnected_calendar_tells_the_model_how_to_connect(tmp_path, monkeypatch):
    monkeypatch.setenv("TOMU_GOOGLE_TOKEN", str(tmp_path / "missing.json"))

    output, is_error = ToolRegistry([google_calendar.calendar_tool]).execute(
        "list_calendar_events", {})

    assert is_error
    assert "isn't" in output and "uv " in output


def test_create_event_adds_it_to_the_primary_calendar(monkeypatch):
    inserted = []

    class Events:
        def insert(self, calendarId, body):
            inserted.append((calendarId, body))
            return Obj(execute=lambda: body | {"htmlLink": "https://calendar.google.com/e"})

    monkeypatch.setattr(google_calendar, "google_api", lambda *args: Obj(events=Events))

    output = google_calendar.create_event("Lunch", "2026-11-20T12:00:00+08:00",
                                          "2026-11-20T13:00:00+08:00", "Cafe")

    assert inserted == [("primary", {"summary": "Lunch", "location": "Cafe",
                                     "start": {"dateTime": "2026-11-20T12:00:00+08:00"},
                                     "end": {"dateTime": "2026-11-20T13:00:00+08:00"}})]
    assert output == "Added: 2026-11-20T12:00:00+08:00  Lunch @ Cafe\nhttps://calendar.google.com/e"
    assert google_calendar.create_event_tool.needs_approval
    assert not google_calendar.calendar_tool.needs_approval
