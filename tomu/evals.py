"""Evals: send a fixed list of messages and check what the agent decided: `uv run tomu-evals`.

Each case in evals/cases.json is a message, plus what a good answer does:
    "tools"     tools it must call, e.g. ["get_current_time"]
    "no_tools"  true if it must answer without calling any tool
    "reply"     words the reply must contain, e.g. ["Singapore"]
    "facts"     facts saved in memory before the message is sent

The exact wording of a reply changes every run, so mostly the decisions are checked:
which tools were called, read from the turn's events. Every case runs with its own
throwaway database, so your real memory is never touched, and every approval is
answered no, so no email is sent and no event is created.
"""

import json
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

from tomu.agent import run_agent
from tomu.events import Emit, Event
from tomu.memory import Memory

CASES_FILE = Path(__file__).parent.parent / "evals" / "cases.json"


def run_evals(emit: Emit, cases: list[dict] | None = None) -> int:
    """Run every case, emit one eval_result per case and an evals_end. Returns how many passed."""
    cases = json.loads(CASES_FILE.read_text()) if cases is None else cases
    started = time.time()
    passed = tokens = 0
    for case in cases:
        events = []
        with tempfile.TemporaryDirectory() as folder:
            memory = Memory(f"{folder}/eval.db")
            for fact in case.get("facts", []):
                memory.remember(fact)
            reply = run_agent(case["message"], events.append, memory)

        problems = check(case, events, reply)
        used = sum(
            e["usage"]["input"] + e["usage"]["output"] for e in events if e["type"] == "llm_call"
        )
        passed += not problems
        tokens += used
        emit(
            {
                "type": "eval_result",
                "message": case["message"],
                "passed": not problems,
                "problems": problems,
                "tools": tools_called(events),
                "reply": reply,
                "tokens": used,
                "model_calls": sum(e["type"] == "llm_call" for e in events),
            }
        )

    emit(
        {
            "type": "evals_end",
            "passed": passed,
            "total": len(cases),
            "tokens": tokens,
            "duration_ms": int((time.time() - started) * 1000),
        }
    )
    return passed


def check(case: dict, events: list[Event], reply: str) -> list[str]:
    """What went wrong, in plain words. An empty list means the case passed."""
    errors = [f"error: {e['message']}" for e in events if e["type"] == "error"]
    if errors:
        return errors  # the turn never finished, so the other checks would only repeat this
    called = tools_called(events)
    problems = []
    for tool in case.get("tools", []):
        if tool not in called:
            problems.append(f"expected {tool}, called {', '.join(called) or 'nothing'}")
    if case.get("no_tools") and called:
        problems.append(f"expected no tools, called {', '.join(called)}")
    for word in case.get("reply", []):
        if word.lower() not in reply.lower():
            problems.append(f"the reply doesn't mention {word!r}")
    return problems


def tools_called(events: list[Event]) -> list[str]:
    return [e["name"] for e in events if e["type"] == "tool_call"]


def show(event: Event) -> None:
    if event["type"] == "eval_result":
        mark = "✓" if event["passed"] else "✗"
        print(f"{mark} {event['message']}")
        for problem in event["problems"]:
            print(f"    {problem}")
    if event["type"] == "evals_end":
        print(
            f"\n{event['passed']}/{event['total']} passed, {event['tokens']} tokens, "
            f"{event['duration_ms'] / 1000:.1f}s"
        )


def main() -> None:
    load_dotenv()
    run_evals(show)


if __name__ == "__main__":
    main()
