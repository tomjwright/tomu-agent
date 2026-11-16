"""The eval runner marks a case passed or failed from the turn's events."""

import json
from types import SimpleNamespace as Obj

from tomu import agent, evals


def fake_client(requests):
    """A model that asks for the time once, then answers with the time."""
    usage = Obj(input_tokens=10, output_tokens=5)

    def create(**request):
        requests.append(request)
        if isinstance(request["messages"][-1]["content"], str):  # the user's message
            return Obj(content=[Obj(type="tool_use", id="t1", name="get_current_time", input={})],
                       stop_reason="tool_use", usage=usage)
        return Obj(content=[Obj(type="text", text="It's noon in Singapore.")],
                   stop_reason="end_turn", usage=usage)

    return lambda: Obj(messages=Obj(create=create))


def test_each_case_passes_or_fails_with_a_reason(monkeypatch):
    requests, events = [], []
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client(requests))
    cases = [
        {"message": "What time is it?", "tools": ["get_current_time"], "reply": ["noon"]},
        {"message": "I live in Singapore", "tools": ["remember"]},
        {"message": "What's 2 + 2?", "no_tools": True, "reply": ["4"]},
    ]

    passed = evals.run_evals(events.append, cases)

    assert passed == 1
    results = [e for e in events if e["type"] == "eval_result"]
    assert [r["passed"] for r in results] == [True, False, False]
    assert results[0]["tools"] == ["get_current_time"]
    assert results[0]["tokens"] == 30  # two model calls of 15 tokens
    assert results[1]["problems"] == ["expected remember, called get_current_time"]
    assert results[2]["problems"] == ["expected no tools, called get_current_time",
                                      "the reply doesn't mention '4'"]
    assert events[-1] | {"duration_ms": 0} == {"type": "evals_end", "passed": 1, "total": 3,
                                               "tokens": 90, "duration_ms": 0}


def test_a_case_starts_with_its_own_facts_and_nothing_else(monkeypatch):
    requests = []
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client(requests))

    evals.run_evals([].append, [{"message": "Where is my home?",
                                 "facts": ["Tom's home is in Singapore"]}])
    evals.run_evals([].append, [{"message": "Where is my home?"}])

    assert "Tom's home is in Singapore" in requests[0]["system"]
    assert "Tom's home is in Singapore" not in requests[2]["system"]  # a fresh database
    assert requests[0]["messages"][0]["content"] == "Where is my home?"  # no old history


def test_every_case_in_the_file_is_well_formed():
    cases = json.loads(evals.CASES_FILE.read_text())
    assert cases
    for case in cases:
        assert isinstance(case["message"], str)
        assert set(case) <= {"message", "tools", "no_tools", "reply", "facts"}
