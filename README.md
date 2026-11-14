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
cd web && npm install && npm run dev            # step timeline on localhost:3000
```

Open http://localhost:3000 and ask a question. As the agent works, its box in
the architecture diagram lights up, and each step appears in the chat as it
happens. The page talks to the API on `localhost:8000`; set
`NEXT_PUBLIC_TOMU_API` to point it somewhere else.

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
| `web/app/page.tsx` | The page: stats and the architecture diagram on the left, the chat and its steps on the right. |
| `web/app/architecture.tsx` | The diagram: lights up each box the turn has passed through, and makes the current one glow. |
| `web/app/step.tsx` | How each event type is drawn as a row in the timeline. |
| `web/app/events.ts` | The event types (mirroring `tomu/events.py`) and `streamChat`, which reads the stream. |

## Checks

`uv run ruff check .` · `uv run pytest` · `cd web && npm run lint && npm run build`
