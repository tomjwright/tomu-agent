"""Terminal chat that prints every step the agent takes: `uv run tomu`."""

import json

from dotenv import load_dotenv

from tomu.agent import run_agent
from tomu.events import Event

DIM, RESET = "\033[2m", "\033[0m"


def show(event: Event) -> None:
    match event["type"]:
        case "memory_recall":
            facts = "skipped" if event["gate"] == "skip" else f"{len(event['facts'])} found"
            print(f"{DIM}  memory: {event['history']} past message(s), facts {facts}{RESET}")
            for fact in event["facts"]:
                print(f"{DIM}    - {fact}{RESET}")
            print(f"{DIM}  skills on offer: {', '.join(event['skills']) or 'none'}{RESET}")
        case "llm_call":
            usage = event["usage"]
            print(f"{DIM}  model call {event['iteration']}: {event['stop_reason']}, "
                  f"{usage['input']} in / {usage['output']} out, {event['duration_ms']}ms{RESET}")
        case "tool_call":
            print(f"{DIM}  tool {event['name']}({json.dumps(event['input'])}){RESET}")
        case "approval_result":
            print(f"{DIM}    {'approved' if event['approved'] else 'declined'}{RESET}")
        case "tool_result":
            status = "ERROR " if event["is_error"] else ""
            print(f"{DIM}    -> {status}{event['output'][:200]} ({event['duration_ms']}ms){RESET}")
        case "turn_end":
            print(f"\ntomu: {event['reply']}")
            ended = f"{event['iterations']} iteration(s), ended by {event['reason']}"
            print(f"{DIM}  ({ended}){RESET}\n")
        case "consolidation_end":
            print(f"{DIM}  consolidated {event['messages']} message(s) into "
                  f"{len(event['facts'])} new fact(s){RESET}")
            for fact in event["facts"]:
                print(f"{DIM}    + {fact}{RESET}")
        case "error":
            print(f"  error: {event['message']}")


def ask(id: str, name: str, args: dict) -> bool:
    answer = input(f"  allow {name}({json.dumps(args)})? [y/N] ")
    return answer.strip().lower() == "y"


def main() -> None:
    load_dotenv()
    while (message := input("you: ").strip()) not in ("", "exit"):
        run_agent(message, show, approve=ask)


if __name__ == "__main__":
    main()
