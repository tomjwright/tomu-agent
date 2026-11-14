"""Skills: procedural memory, the agent's how-to notes, kept as plain Markdown.

Each skill is a folder in skills/ holding a SKILL.md file:

    ---
    name: meeting-planner
    description: Schedule a meeting with people in other cities or countries.
    ---
    Step-by-step instructions for the model...

The retrieval gate loads a skill only when the message shares a word with its
description, so each turn's prompt carries only the skills that fit it.
"""

from dataclasses import dataclass
from pathlib import Path

from tomu.memory import keywords

SKILLS_DIR = Path(__file__).parent.parent / "skills"


@dataclass
class Skill:
    name: str
    description: str
    instructions: str


def parse_skill(text: str) -> Skill:
    _, header, instructions = text.split("---", 2)
    fields = dict(line.split(":", 1) for line in header.strip().splitlines())
    return Skill(fields["name"].strip(), fields["description"].strip(), instructions.strip())


def load_skills(folder: Path = SKILLS_DIR) -> list[Skill]:
    return [parse_skill(path.read_text()) for path in sorted(folder.glob("*/SKILL.md"))]


def stems(text: str) -> set[str]:
    # "meeting" and "meetings" count as the same word
    return {word.removesuffix("s") for word in keywords(text)}


def pick_skills(message: str, skills: list[Skill]) -> list[Skill]:
    words = stems(message)
    return [skill for skill in skills if words & stems(skill.description)]
