"""One agent turn: memory, the model, the system prompt and the tools, wired into the loop."""

import os

import anthropic

from tomu.events import Emit
from tomu.loop import run_loop
from tomu.memory import Memory, remember_tool
from tomu.tools import ToolRegistry, current_time_tool

SYSTEM_PROMPT = (
    "You are Tomu, a helpful personal assistant running on the user's own machine. "
    "Use tools when they help; be concise. When the user tells you something about "
    "themselves that is worth keeping, save it with the remember tool."
)

memory = Memory(os.getenv("TOMU_DB", "tomu.db"))


def system_prompt(facts: list[str]) -> str:
    if not facts:
        return SYSTEM_PROMPT
    remembered = "\n".join(f"- {fact}" for fact in facts)
    return f"{SYSTEM_PROMPT}\n\nThings you remember about the user:\n{remembered}"


def run_agent(message: str, emit: Emit, memory: Memory = memory) -> str:
    emit({"type": "turn_start", "message": message})
    try:
        # working memory: recent history plus any facts the retrieval gate found
        history = memory.history()
        facts = memory.recall(message)
        emit({"type": "memory_recall", "history": len(history),
              "gate": "skip" if facts is None else "retrieve", "facts": facts or []})

        reply = run_loop(
            call_model=anthropic.Anthropic().messages.create,
            model=os.getenv("TOMU_MODEL", "claude-sonnet-4-6"),
            system=system_prompt(facts or []),
            messages=[*history, {"role": "user", "content": message}],
            tools=ToolRegistry([current_time_tool, remember_tool(memory)]),
            emit=emit,
        )

        if reply:  # the API rejects empty messages, so an empty reply isn't kept
            memory.save_turn(message, reply)
            emit({"type": "memory_save"})
        return reply
    except Exception as exc:
        emit({"type": "error", "message": str(exc)})
        return ""
