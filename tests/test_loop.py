from types import SimpleNamespace as Obj

from tomu.loop import run_loop
from tomu.tools import Tool, ToolRegistry

echo = Tool(
    name="echo",
    description="Echo the text back",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
    run=lambda text: f"echo: {text}",
)


def response(blocks, stop_reason):
    return Obj(content=blocks, stop_reason=stop_reason,
               usage=Obj(input_tokens=10, output_tokens=5))


def text(t):
    return response([Obj(type="text", text=t)], "end_turn")


def tool_use(name, args):
    return response([Obj(type="tool_use", id="t1", name=name, input=args)], "tool_use")


def run(responses, max_iterations=10):
    """Run the loop against a fake model that replies with `responses` in order."""
    events, requests = [], []

    def fake_model(**request):
        requests.append(request)
        return responses.pop(0)

    messages = [{"role": "user", "content": "hi"}]
    reply = run_loop(fake_model, "test-model", "system", messages, ToolRegistry([echo]),
                     events.append, max_iterations=max_iterations)
    return reply, events, requests, messages


def types(events):
    return [e["type"] for e in events]


def test_answers_straight_away_when_no_tools_are_needed():
    reply, events, _, _ = run([text("hello")])
    assert reply == "hello"
    assert types(events) == ["llm_call", "turn_end"]
    assert events[-1]["reason"] == "no_tool_calls"


def test_runs_a_tool_and_feeds_the_result_back():
    reply, events, _, messages = run([tool_use("echo", {"text": "x"}), text("done")])
    assert reply == "done"
    assert types(events) == ["llm_call", "tool_call", "tool_result", "llm_call", "turn_end"]
    assert events[2]["output"] == "echo: x"
    assert messages[2]["content"][0]["tool_use_id"] == "t1"


def test_unknown_tool_becomes_an_error_result():
    _, events, _, _ = run([tool_use("nope", {}), text("sorry")])
    assert events[2]["is_error"] is True
    assert events[2]["output"] == "Unknown tool: nope"


def test_stops_at_max_iterations_with_one_tools_off_call():
    reply, events, requests, _ = run(
        [tool_use("echo", {"text": "1"}), tool_use("echo", {"text": "2"}), text("best effort")],
        max_iterations=2,
    )
    assert reply == "best effort"
    assert requests[-1]["tool_choice"] == {"type": "none"}
    assert events[-1]["reason"] == "max_iterations"
    assert events[-1]["iterations"] == len(requests) == 3
