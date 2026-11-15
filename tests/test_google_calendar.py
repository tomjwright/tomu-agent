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
