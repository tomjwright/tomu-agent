"""One agent turn: the model, the system prompt and the tools, wired into the loop."""

import os

import anthropic

from tomu.events import Emit
from tomu.loop import run_loop
from tomu.tools import ToolRegistry, current_time_tool

SYSTEM_PROMPT = (
    "You are Tomu, a helpful personal assistant running on the user's own machine. "
    "Use tools when they help; be concise."
)


def run_agent(message: str, emit: Emit) -> str:
    emit({"type": "turn_start", "message": message})
    try:
        return run_loop(
            call_model=anthropic.Anthropic().messages.create,
            model=os.getenv("TOMU_MODEL", "claude-sonnet-4-6"),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
            tools=ToolRegistry([current_time_tool]),
            emit=emit,
        )
    except Exception as exc:
        emit({"type": "error", "message": str(exc)})
        return ""
