"""The release gate opens only when every test passes and enough evals pass."""

import json
from types import SimpleNamespace as Obj

from tomu import agent, evals, gate
from tomu.memory import Memory


def model_that_answers(text):
    usage = Obj(input_tokens=10, output_tokens=5)
    reply = Obj(content=[Obj(type="text", text=text)], stop_reason="end_turn", usage=usage)
    return lambda: Obj(messages=Obj(create=lambda **request: reply))


def use_cases(monkeypatch, tmp_path, cases):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases))
    monkeypatch.setattr(evals, "CASES_FILE", path)


def test_a_failing_test_closes_the_gate_without_running_evals(monkeypatch, tmp_path):
    memory, events = Memory(str(tmp_path / "tomu.db")), []
    monkeypatch.setattr(gate, "run_tests", lambda: (47, 1))
    monkeypatch.setattr(evals, "run_evals", lambda *args: 1 / 0)  # must not be called

    assert gate.run_gate(events.append, memory) is False

    assert [e["type"] for e in events] == ["gate_tests", "gate_result"]
    assert events[-1]["reason"] == "1 test(s) failed, so the evals didn't run"
    assert memory.gate_runs()[0]["open"] is False


def test_the_gate_opens_only_when_enough_evals_pass(monkeypatch, tmp_path):
    memory = Memory(str(tmp_path / "tomu.db"))
    monkeypatch.setattr(gate, "run_tests", lambda: (48, 0))
    monkeypatch.setattr(agent.anthropic, "Anthropic", model_that_answers("It's 4."))
    use_cases(monkeypatch, tmp_path, [{"message": "What's 2 + 2?", "reply": ["4"]}] * 4
              + [{"message": "What's 2 + 2?", "reply": ["five"]}])

    events = []
    assert gate.run_gate(events.append, memory) is True  # 4/5 passed, 4 needed
    assert events[-1]["reason"] == "4/5 evals passed, 4 needed"
    assert [e["type"] for e in events].count("eval_result") == 5

    use_cases(monkeypatch, tmp_path, [{"message": "What's 2 + 2?", "reply": ["five"]}] * 2)
    assert gate.run_gate([].append, memory) is False

    assert [run["open"] for run in memory.gate_runs()] == [False, True]  # newest first


def test_run_tests_reads_pytest_summary(monkeypatch):
    summary = "....F\n48 passed, 2 failed, 1 skipped, 1 error in 2.10s\n"
    monkeypatch.setattr(gate.subprocess, "run", lambda *args, **kwargs: Obj(stdout=summary))

    assert gate.run_tests() == (48, 3)
