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
    approval_request {"id", "name", "input"}          the tool changes something, so
                                                      the loop waits for your yes or no
    approval_result  {"id", "name", "approved"}       your answer (no answer in time
                                                      counts as no)
    tool_result  {"id", "name", "output", "is_error", the tool's answer
                  "duration_ms"}
    turn_end     {"reply", "iterations", "reason"}    reason: "no_tool_calls"
                                                      or "max_iterations"
    memory_save  {}                                   the turn was saved to history
    consolidation_start {"messages"}                  20 new messages built up (or you
                                                      pressed Consolidate), so the model
                                                      reads them for lasting facts
    consolidation_end {"messages", "facts",           the new facts it saved
                       "usage", "duration_ms"}
    error        {"message"}                          the turn failed
"""

from collections.abc import Callable

Event = dict
Emit = Callable[[Event], None]
