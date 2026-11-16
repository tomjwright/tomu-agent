from tomu.memory import Memory, remember_tool


def test_history_returns_the_latest_messages_oldest_first(tmp_path):
    memory = Memory(str(tmp_path / "tomu.db"))
    memory.save_turn("first", "one")
    memory.save_turn("second", "two")

    assert memory.history(limit=2) == [
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "two"},
    ]


def test_recall_finds_facts_that_share_a_word_with_the_message(tmp_path):
    memory = Memory(str(tmp_path / "tomu.db"))
    remember_tool(memory).run(fact="Tom lives in Singapore")
    memory.remember("Tom's favourite food is laksa")

    assert memory.recall("What's the weather like in Singapore?") == ["Tom lives in Singapore"]
    assert memory.recall("Book me a flight to Paris") == []


def test_gate_skips_the_lookup_when_there_is_nothing_to_search_for(tmp_path):
    memory = Memory(str(tmp_path / "tomu.db"))
    memory.remember("Tom lives in Singapore")

    assert memory.recall("hi, thanks!") is None


def test_a_saved_trace_comes_back_with_its_events_in_order(tmp_path):
    memory = Memory(str(tmp_path / "tomu.db"))
    memory.save_trace("first", [{"type": "turn_start", "at": 1.0}])
    memory.save_trace("second", [{"type": "turn_start", "at": 2.0},
                                 {"type": "turn_end", "at": 3.0}])

    assert [t["message"] for t in memory.traces()] == ["second", "first"]
    newest = memory.traces()[0]["id"]
    assert [e["type"] for e in memory.trace(newest)] == ["turn_start", "turn_end"]
    assert memory.trace(999) is None
