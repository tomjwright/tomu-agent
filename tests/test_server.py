"""The API streams each event the agent emits as one Server-Sent Event."""

import json

from tomu import server


def fake_run_agent(message, emit):
    emit({"type": "turn_start", "message": message})
    emit({"type": "turn_end", "reply": "hi", "iterations": 1, "reason": "no_tool_calls"})
    return "hi"


def test_stream_turn_sends_each_event_as_sse(monkeypatch):
    monkeypatch.setattr(server, "run_agent", fake_run_agent)

    chunks = list(server.stream_turn("hello"))

    assert all(c.startswith("data: ") and c.endswith("\n\n") for c in chunks)
    events = [json.loads(c.removeprefix("data: ")) for c in chunks]
    assert [e["type"] for e in events] == ["turn_start", "turn_end"]
    assert events[0]["message"] == "hello"
    assert all("at" in e for e in events)
