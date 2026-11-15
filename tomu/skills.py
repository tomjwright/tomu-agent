"""Skills: procedural memory, the agent's how-to notes, kept as plain Markdown.

Each skill is a folder in skills/ holding a SKILL.md file:

    ---
    name: meeting-planner
    description: Schedule a meeting with people in other cities or countries.
    ---
    Step-by-step instructions for the model...

Every turn the model sees each skill's name and description. When one fits the
request, the model calls the use_skill tool to read its full instructions, so
choosing a skill is the model's decision and shows up as a tool call.
"""

from dataclasses import dataclass
from pathlib import Path

from tomu.tools import Tool

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


def use_skill_tool(skills: list[Skill]) -> Tool:
    by_name = {skill.name: skill for skill in skills}

    def use_skill(name: str) -> str:
        if name not in by_name:
            raise ValueError(f"no skill called {name!r}")
        return by_name[name].instructions

    return Tool(
        name="use_skill",
        description="Read a skill's step-by-step instructions before doing a task it covers.",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The skill's name."}},
            "required": ["name"],
        },
        run=use_skill,
    )
