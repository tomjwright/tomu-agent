# tomu-agent

A local AI agent that shows its work. Every step it takes (each model call,
each tool call and result, and why it stopped) is emitted as an event you can
watch. Inspired by [waku-agent](https://github.com/ShenSeanChen/waku-agent).

## Run it

```bash
uv sync
cp .env.example .env                            # add your ANTHROPIC_API_KEY
uv run tomu                                     # terminal chat that prints each step
uv run uvicorn tomu.server:app --reload         # API on localhost:8000
```

Stream a turn's steps from the API:

```bash
curl -N -X POST localhost:8000/api/chat \
  -H 'content-type: application/json' -d '{"message":"what time is it in Tokyo?"}'
```

## How it works

| File | What it does |
|---|---|
| `tomu/loop.py` | The loop: call the model, run the tools it asks for, feed the results back, repeat. |
| `tomu/events.py` | The events the loop emits: `turn_start`, `llm_call`, `tool_call`, `tool_result`, `turn_end`, `error`. |
| `tomu/tools.py` | The `Tool` type, the registry that runs tools, and the demo `get_current_time` tool. |
| `tomu/agent.py` | `run_agent(message, emit)`: wires the Anthropic client, system prompt and tools into the loop. |
| `tomu/server.py` | `POST /api/chat`: runs a turn and streams its events as Server-Sent Events. |
| `tomu/cli.py` | The terminal chat. |

## Checks

`uv run ruff check .` · `uv run pytest`
