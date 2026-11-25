"""Consolidation turns messages into facts once 20 have built up, and never reads one twice."""

from types import SimpleNamespace as Obj

from tomu import agent
from tomu.consolidate import consolidate
from tomu.memory import Memory


def fake_model(text, requests):
    def create(**request):
        requests.append(request)
        return Obj(
            content=[Obj(type="text", text=text)],
            stop_reason="end_turn",
            usage=Obj(input_tokens=100, output_tokens=10),
        )

    return create


def chat(memory, turns, start=0):
    for i in range(start, start + turns):
        memory.save_turn(f"message {i}", f"reply {i}")


def test_waits_for_twenty_new_messages_then_saves_the_facts(tmp_path):
    memory, requests, events = Memory(str(tmp_path / "tomu.db")), [], []
    memory.remember("Tom lives in Singapore")
    model = fake_model("Tom's sister is called Amy\n- Tom swims on Sundays", requests)
    chat(memory, 9)

    assert consolidate(memory, events.append, model, "m") == []  # 18 messages: not yet
    assert requests == [] and events == []

    chat(memory, 1, start=9)
    assert consolidate(memory, events.append, model, "m") == [
        "Tom's sister is called Amy",
        "Tom swims on Sundays",
    ]

    assert "- Tom lives in Singapore" in requests[0]["messages"][0]["content"]  # known facts
    assert "user: message 9" in requests[0]["messages"][0]["content"]
    assert memory.recall("Who is Amy?") == ["Tom's sister is called Amy"]
    assert [e["type"] for e in events] == ["consolidation_start", "consolidation_end"]
    assert events[1]["messages"] == 20


def test_never_reads_the_same_messages_twice(tmp_path):
    memory, requests, events = Memory(str(tmp_path / "tomu.db")), [], []
    chat(memory, 10)
    consolidate(memory, events.append, fake_model("NONE", requests), "m")

    assert memory.all_facts() == []  # NONE saves nothing
    assert memory.unconsolidated()[0] == []
    consolidate(memory, events.append, fake_model("NONE", requests), "m", force=True)
    assert len(requests) == 1  # the button with nothing new doesn't call the model
    assert events[-1]["messages"] == 0

    chat(memory, 1, start=10)
    consolidate(memory, events.append, fake_model("NONE", requests), "m", force=True)
    assert "message 0" not in requests[1]["messages"][0]["content"]
    assert requests[1]["messages"][0]["content"].count("user:") == 1


def test_a_failed_model_call_leaves_the_messages_for_next_time(tmp_path):
    memory, events = Memory(str(tmp_path / "tomu.db")), []
    chat(memory, 10)

    def broken(**request):
        raise RuntimeError("overloaded")

    assert consolidate(memory, events.append, broken, "m") == []
    assert events[-1] == {"type": "error", "message": "Consolidation failed: overloaded"}
    assert len(memory.unconsolidated()[0]) == 20


def test_two_consolidations_at_once_never_read_the_same_messages(tmp_path):
    memory, requests, events = Memory(str(tmp_path / "tomu.db")), [], []
    chat(memory, 10)
    model = fake_model("Tom likes laksa", requests)

    def slow_model(**request):  # a second run (say, from Telegram) starts mid-call
        assert consolidate(memory, events.append, model, "m", force=True) == []
        return model(**request)

    consolidate(memory, events.append, slow_model, "m")

    assert len(requests) == 1 and memory.all_facts() == ["Tom likes laksa"]
    messages, done, newest = memory.unconsolidated()
    assert not memory.claim(0, newest)  # a mark that already moved can't be claimed again


def test_a_turn_consolidates_by_itself_when_twenty_messages_built_up(tmp_path, monkeypatch):
    memory, requests, events = Memory(str(tmp_path / "tomu.db")), [], []
    model = fake_model("Tom likes laksa", requests)
    monkeypatch.setattr(agent.anthropic, "Anthropic", lambda: Obj(messages=Obj(create=model)))
    chat(memory, 9)

    agent.run_agent("I love laksa", events.append, memory, skills=[])

    assert [e["type"] for e in events][-3:] == [
        "memory_save",
        "consolidation_start",
        "consolidation_end",
    ]
    assert memory.all_facts() == ["Tom likes laksa"]
