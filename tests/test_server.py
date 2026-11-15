"""The API streams each event the agent emits as one Server-Sent Event."""

import json

import pytest

from tomu import server


def fake_run_agent(message, emit, approve):
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


def run_agent_that_asks(answers):
    def fake(message, emit, approve):
        emit({"type": "approval_request", "id": "t1", "name": "send", "input": {}})
        answers.append(approve("t1", "send", {}))
    return fake


def test_a_turn_waits_for_the_answer_posted_to_approve(monkeypatch):
    answers = []
    monkeypatch.setattr(server, "run_agent", run_agent_that_asks(answers))

    stream = server.stream_turn("send it")
    assert json.loads(next(stream).removeprefix("data: "))["type"] == "approval_request"
    assert server.approve(server.ApprovalAnswer(id="t1", approved=True)) == {"ok": True}
    assert list(stream) == []

    assert answers == [True]
    assert server.waiting == {}


def test_no_answer_in_time_counts_as_no(monkeypatch):
    answers = []
    monkeypatch.setattr(server, "run_agent", run_agent_that_asks(answers))
    monkeypatch.setattr(server, "APPROVAL_TIMEOUT", 0.05)

    list(server.stream_turn("send it"))

    assert answers == [False]


def test_answering_something_that_is_not_waiting_is_a_404():
    with pytest.raises(server.HTTPException) as error:
        server.approve(server.ApprovalAnswer(id="nope", approved=True))
    assert error.value.status_code == 404
