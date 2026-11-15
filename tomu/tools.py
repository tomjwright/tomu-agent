"""Tools the agent can call, and the registry that runs them."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict  # JSON schema for the tool's arguments
    run: Callable[..., str]
    needs_approval: bool = False  # True for tools that change something: you must say yes first


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self.tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict]:
        """The tool list in the shape the Anthropic API expects."""
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self.tools.values()
        ]

    def needs_approval(self, name: str) -> bool:
        tool = self.tools.get(name)
        return tool is not None and tool.needs_approval

    def execute(self, name: str, args: dict) -> tuple[str, bool]:
        """Run a tool and return (output, is_error). Never raises: a failing
        tool becomes an error message the model can read and react to."""
        tool = self.tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}", True
        try:
            return tool.run(**args), False
        except Exception as exc:
            return f"Tool failed: {exc}", True


def get_current_time(time_zone: str = "UTC") -> str:
    return datetime.now(ZoneInfo(time_zone)).strftime("%A %d %B %Y, %H:%M %Z")


current_time_tool = Tool(
    name="get_current_time",
    description="Get the current date and time in a given IANA time zone.",
    input_schema={
        "type": "object",
        "properties": {
            "time_zone": {"type": "string", "description": "e.g. Asia/Singapore. Default UTC."}
        },
    },
    run=get_current_time,
)
