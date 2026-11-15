"""One agent turn: memory, the model, the system prompt and the tools, wired into the loop."""

import os

import anthropic

from tomu.events import Emit
from tomu.gmail import read_email_tool, search_email_tool, send_email_tool
from tomu.google_calendar import calendar_tool, create_event_tool
from tomu.loop import Approve, run_loop
from tomu.memory import Memory, remember_tool
from tomu.skills import Skill, load_skills, use_skill_tool
from tomu.tools import ToolRegistry, current_time_tool

SYSTEM_PROMPT = (
    "You are Tomu, a helpful personal assistant running on the user's own machine. "
    "Use tools when they help; be concise. When the user tells you something about "
    "themselves that is worth keeping, save it with the remember tool."
)


def system_prompt(facts: list[str], skills: list[Skill]) -> str:
    prompt = SYSTEM_PROMPT
    if facts:
        remembered = "\n".join(f"- {fact}" for fact in facts)
        prompt += f"\n\nThings you remember about the user:\n{remembered}"
    if skills:
        listed = "\n".join(f"- {skill.name}: {skill.description}" for skill in skills)
        prompt += ("\n\nSkills you can use. When one fits the request, call use_skill "
                   f"with its name and follow the instructions it returns:\n{listed}")
    return prompt


def run_agent(message: str, emit: Emit, memory: Memory | None = None,
              skills: list[Skill] | None = None,
              approve: Approve = lambda id, name, input: False) -> str:
    # read TOMU_DB per turn, after the CLI or server has loaded .env
    memory = memory or Memory(os.getenv("TOMU_DB", "tomu.db"))
    emit({"type": "turn_start", "message": message})
    try:
        skills = load_skills() if skills is None else skills
        # working memory: recent history, the facts the retrieval gate found, and the skill list
        history = memory.history()
        facts = memory.recall(message)
        emit({"type": "memory_recall", "history": len(history),
              "gate": "skip" if facts is None else "retrieve", "facts": facts or [],
              "skills": [skill.name for skill in skills]})

        reply = run_loop(
            call_model=anthropic.Anthropic().messages.create,
            model=os.getenv("TOMU_MODEL", "claude-sonnet-4-6"),
            system=system_prompt(facts or [], skills),
            messages=[*history, {"role": "user", "content": message}],
            tools=ToolRegistry([current_time_tool, calendar_tool, create_event_tool,
                                search_email_tool, read_email_tool, send_email_tool,
                                remember_tool(memory), use_skill_tool(skills)]),
            emit=emit,
            approve=approve,
        )

        if reply:  # the API rejects empty messages, so an empty reply isn't kept
            memory.save_turn(message, reply)
            emit({"type": "memory_save"})
        return reply
    except Exception as exc:
        emit({"type": "error", "message": str(exc)})
        return ""
