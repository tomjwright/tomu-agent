"""THE LOOP: reason -> act -> observe -> repeat.

    while True:
        response = model(messages, tools)       # reason
        if response asks for no tools:
            return response text                 # answer the human
        results = run(the tools it asked for)    # act
        messages += results                      # observe

Two ways out (the guardrails):
  1. the model answers without asking for a tool -> normal end of turn
  2. max_iterations reached -> one last call with tools switched off, so the
     model answers from what it has gathered instead of looping forever

Every step is passed to `emit` as an event (see events.py), which is how the
terminal and the frontend can show what the agent is doing.
"""

import time
from collections.abc import Callable

from tomu.events import Emit
from tomu.tools import ToolRegistry

LIMIT_NOTE = (
    "You have reached the step limit and cannot call more tools. "
    "Answer now from what you already gathered, and say what is missing."
)


def run_loop(
    call_model: Callable,  # e.g. anthropic.Anthropic().messages.create
    model: str,
    system: str,
    messages: list[dict],
    tools: ToolRegistry,
    emit: Emit,
    max_iterations: int = 10,
    max_tokens: int = 2048,
) -> str:
    def ask_model(iteration: int, **overrides):
        started = time.perf_counter()
        request = dict(model=model, system=system, messages=messages,
                       tools=tools.schemas(), max_tokens=max_tokens)
        response = call_model(**(request | overrides))
        emit({
            "type": "llm_call",
            "iteration": iteration,
            "text": text_of(response),
            "stop_reason": response.stop_reason,
            "usage": {"input": response.usage.input_tokens,
                      "output": response.usage.output_tokens},
            "duration_ms": ms_since(started),
        })
        messages.append({"role": "assistant", "content": response.content})
        return response

    for iteration in range(1, max_iterations + 1):
        # reason
        response = ask_model(iteration)
        tool_calls = [block for block in response.content if block.type == "tool_use"]

        # guardrail 1: no tool calls means the model is answering the human
        if not tool_calls:
            reply = text_of(response)
            emit({"type": "turn_end", "reply": reply, "iterations": iteration,
                  "reason": "no_tool_calls"})
            return reply

        # act, then observe: run each tool and hand the results back
        results = []
        for call in tool_calls:
            emit({"type": "tool_call", "iteration": iteration, "id": call.id,
                  "name": call.name, "input": call.input})
            started = time.perf_counter()
            output, is_error = tools.execute(call.name, call.input)
            emit({"type": "tool_result", "id": call.id, "name": call.name, "output": output,
                  "is_error": is_error, "duration_ms": ms_since(started)})
            results.append({"type": "tool_result", "tool_use_id": call.id,
                            "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    # guardrail 2: out of iterations, so one last call with tools switched off
    final = ask_model(max_iterations + 1, system=f"{system}\n\n{LIMIT_NOTE}",
                      tool_choice={"type": "none"})
    reply = text_of(final)
    emit({"type": "turn_end", "reply": reply, "iterations": max_iterations + 1,
          "reason": "max_iterations"})
    return reply


def text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def ms_since(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
