"""Consolidation: turn old conversation (episodic memory) into lasting facts
(semantic memory), a bit like sleep does for people.

The agent only sees the last 20 messages, so anything said before that is lost
unless it became a fact. Consolidation hands the model the messages it hasn't
read yet, plus the facts already known, asks which new lasting facts they
contain, and saves each one. Later turns find them through the retrieval gate.

It runs at the end of a turn once CONSOLIDATE_EVERY new messages have built up,
and whenever you press Consolidate on the page. History is never deleted.
"""

import time
from collections.abc import Callable

from tomu.events import Emit
from tomu.memory import Memory

CONSOLIDATE_EVERY = 20  # the size of the history window, so nothing scrolls out unread

PROMPT = (
    "You keep the long-term memory of a personal assistant. Read the conversation and "
    "list new lasting facts about the user that will help in future conversations: "
    "preferences, people, places, plans and routines. Write one short sentence per line, "
    "with no bullets. Skip facts already known, small talk and one-off requests. "
    "If there is nothing new, reply with just NONE."
)


def consolidate(memory: Memory, emit: Emit, call_model: Callable, model: str,
                force: bool = False) -> list[str]:
    """Save the lasting facts in messages not yet consolidated, and return them.
    Unless `force` is set, it waits until CONSOLIDATE_EVERY messages have built up."""
    messages, newest = memory.unconsolidated()
    if not force and len(messages) < CONSOLIDATE_EVERY:
        return []
    emit({"type": "consolidation_start", "messages": len(messages)})
    started, facts, usage = time.perf_counter(), [], {"input": 0, "output": 0}
    if messages:
        try:
            response = call_model(
                model=model, max_tokens=1024, system=PROMPT,
                messages=[{"role": "user", "content": transcript(memory.all_facts(), messages)}],
            )
        except Exception as exc:  # not marked as done, so these messages are tried again
            emit({"type": "error", "message": f"Consolidation failed: {exc}"})
            return []
        text = "".join(block.text for block in response.content if block.type == "text")
        facts = [line.strip("-* ").strip() for line in text.splitlines()]
        facts = [fact for fact in facts if fact and fact.upper() != "NONE"]
        for fact in facts:
            memory.remember(fact)
        memory.mark_consolidated(newest)
        usage = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
    emit({"type": "consolidation_end", "messages": len(messages), "facts": facts,
          "usage": usage, "duration_ms": round((time.perf_counter() - started) * 1000)})
    return facts


def transcript(known: list[str], messages: list[dict]) -> str:
    facts = "\n".join(f"- {fact}" for fact in known) or "(none yet)"
    lines = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    return f"Facts already known:\n{facts}\n\nConversation:\n{lines}"
