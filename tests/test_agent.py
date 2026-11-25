"""run_agent loads memory before the loop and saves the turn after it."""

from types import SimpleNamespace as Obj

from tomu import agent
from tomu.memory import Memory
from tomu.skills import Skill, load_skills


def fake_client(requests):
    def create(**request):
        requests.append(request)
        return Obj(
            content=[Obj(type="text", text="You live in Singapore.")],
            stop_reason="end_turn",
            usage=Obj(input_tokens=10, output_tokens=5),
        )

    return lambda: Obj(messages=Obj(create=create))


def test_turn_uses_history_and_facts_then_saves_itself(tmp_path, monkeypatch):
    requests, events = [], []
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client(requests))
    memory = Memory(str(tmp_path / "tomu.db"))
    memory.save_turn("hello", "hi Tom")
    memory.remember("Tom lives in Singapore")

    skills = [
        Skill("weather", "Weather forecasts", "Check the forecast first."),
        Skill("email", "Draft an email reply", "Keep it short."),
    ]

    agent.run_agent("Where do I live? Singapore?", events.append, memory, skills)

    assert [e["type"] for e in events] == [
        "turn_start",
        "memory_recall",
        "llm_call",
        "turn_end",
        "memory_save",
    ]
    assert events[1] == {
        "type": "memory_recall",
        "history": 2,
        "gate": "retrieve",
        "facts": ["Tom lives in Singapore"],
        "skills": ["weather", "email"],
    }
    assert "Tom lives in Singapore" in requests[0]["system"]
    # the model sees each skill's description, and reads the instructions with use_skill
    assert "- email: Draft an email reply" in requests[0]["system"]
    assert "Keep it short." not in requests[0]["system"]
    assert "use_skill" in [tool["name"] for tool in requests[0]["tools"]]
    assert requests[0]["messages"][0] == {"role": "user", "content": "hello"}
    assert memory.history()[-1] == {"role": "assistant", "content": "You live in Singapore."}


def test_a_turn_saves_its_events_as_a_trace_for_replay(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client([]))
    memory = Memory(str(tmp_path / "tomu.db"))

    agent.run_agent("Where do I live?", events.append, memory, skills=[])

    [saved] = memory.traces()
    assert saved["message"] == "Where do I live?"
    trace = memory.trace(saved["id"])
    assert [e["type"] for e in trace] == [e["type"] for e in events]
    assert all("at" in e for e in trace)
    assert all("at" not in e for e in events)  # what the gateways see is unchanged


def test_a_broken_skill_file_ends_the_turn_with_an_error(tmp_path, monkeypatch):
    events = []
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("no header here")
    monkeypatch.setattr(agent, "load_skills", lambda: load_skills(tmp_path))

    agent.run_agent("hello", events.append, Memory(str(tmp_path / "tomu.db")))

    assert [e["type"] for e in events] == ["turn_start", "error"]
    [saved] = Memory(str(tmp_path / "tomu.db")).traces()  # failed turns are kept too
    assert saved["message"] == "hello"


def test_a_trace_that_cannot_be_saved_does_not_break_the_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client([]))
    memory = Memory(str(tmp_path / "tomu.db"))

    def broken_save_trace(message, events):
        raise OSError("disk full")

    monkeypatch.setattr(memory, "save_trace", broken_save_trace)

    reply = agent.run_agent("Where do I live?", [].append, memory, skills=[])
    assert reply == "You live in Singapore."
