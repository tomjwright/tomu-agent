"""run_agent loads memory before the loop and saves the turn after it."""

from types import SimpleNamespace as Obj

from tomu import agent
from tomu.memory import Memory
from tomu.skills import Skill


def fake_client(requests):
    def create(**request):
        requests.append(request)
        return Obj(content=[Obj(type="text", text="You live in Singapore.")],
                   stop_reason="end_turn", usage=Obj(input_tokens=10, output_tokens=5))

    return lambda: Obj(messages=Obj(create=create))


def test_turn_uses_history_and_facts_then_saves_itself(tmp_path, monkeypatch):
    requests, events = [], []
    monkeypatch.setattr(agent.anthropic, "Anthropic", fake_client(requests))
    memory = Memory(str(tmp_path / "tomu.db"))
    memory.save_turn("hello", "hi Tom")
    memory.remember("Tom lives in Singapore")

    skills = [Skill("weather", "Weather forecasts", "Check the forecast first."),
              Skill("email", "Draft an email reply", "Keep it short.")]

    agent.run_agent("Where do I live? Singapore? Any weather tips?", events.append, memory, skills)

    assert [e["type"] for e in events] == [
        "turn_start", "memory_recall", "llm_call", "turn_end", "memory_save"]
    assert events[1] == {"type": "memory_recall", "history": 2, "gate": "retrieve",
                              "facts": ["Tom lives in Singapore"], "skills": ["weather"]}
    assert "Tom lives in Singapore" in requests[0]["system"]
    assert "Check the forecast first." in requests[0]["system"]
    assert "Keep it short." not in requests[0]["system"]
    assert requests[0]["messages"][0] == {"role": "user", "content": "hello"}
    assert memory.history()[-1] == {"role": "assistant", "content": "You live in Singapore."}
