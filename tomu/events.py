"""The steps an agent turn emits, in the order they happen.

Each event is a plain dict with a "type", so it can be printed in the terminal
or sent to the browser as JSON without any conversion.

    turn_start   {"message"}                          the user's message arrived
    memory_recall {"history", "gate", "facts",        working memory was assembled:
                   "skills"}                          past messages loaded, and the
                                                      retrieval gate's decision
                                                      ("retrieve" or "skip"), the facts
                                                      found, and the skills on offer
    llm_call     {"iteration", "text", "stop_reason", one call to the model
                  "usage": {"input", "output"}, "duration_ms"}
    tool_call    {"iteration", "id", "name", "input"} the model asked for a tool
    tool_result  {"id", "name", "output", "is_error", the tool's answer
                  "duration_ms"}
    turn_end     {"reply", "iterations", "reason"}    reason: "no_tool_calls"
                                                      or "max_iterations"
    memory_save  {}                                   the turn was saved to history
    error        {"message"}                          the turn failed
"""

from collections.abc import Callable

Event = dict
Emit = Callable[[Event], None]
