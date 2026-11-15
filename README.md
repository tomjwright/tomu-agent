# tomu-agent

A local AI agent that shows its work. Every step it takes (what it recalled from
memory, each model call, each tool call and result, and why it stopped) is
emitted as an event you can watch. Inspired by [waku-agent](https://github.com/ShenSeanChen/waku-agent).

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
happens. Tell it something about yourself ("I live in Singapore") and it saves
a fact; ask a related question later and you'll see the retrieval gate find it.
Ask it to set up a meeting and the model reads the `meeting-planner` skill
with the `use_skill` tool, so the Procedural box lights up.
To let it read your Google Calendar and Gmail, add a Google OAuth "Desktop app" client to
`.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; see `.env.example`), then run
`uv sync --extra google` and `uv run tomu-google` once to sign in. Your login
token stays on your machine in `google-token.json`. Access is read-only.

The page talks to the API on `localhost:8000`; set
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
| `tomu/events.py` | The events a turn emits: `turn_start`, `memory_recall`, `llm_call`, `tool_call`, `tool_result`, `turn_end`, `memory_save`, `error`. |
| `tomu/tools.py` | The `Tool` type, the registry that runs tools, and the demo `get_current_time` tool. |
| `tomu/memory.py` | Memory in one SQLite file (`tomu.db`, or `TOMU_DB`): chat history, facts with full-text search, the retrieval gate and the `remember` tool. |
| `tomu/skills.py` | Skills (procedural memory): loads every `skills/<name>/SKILL.md`, and the `use_skill` tool the model calls to read one. |
| `skills/` | The skills themselves, as plain Markdown: a `name` and `description` header, then instructions for the model. |
| `tomu/google_auth.py` | `uv run tomu-google`, which signs you in to Google (read-only), and the shared login the Google tools use. |
| `tomu/google_calendar.py` | The read-only `list_calendar_events` tool. |
| `tomu/gmail.py` | The read-only `search_email` and `read_email` tools. |
| `tomu/agent.py` | `run_agent(message, emit)`: loads memory, wires the Anthropic client, system prompt and tools into the loop, then saves the turn. |
| `tomu/server.py` | `POST /api/chat`: runs a turn and streams its events as Server-Sent Events. |
| `tomu/cli.py` | The terminal chat. |
| `web/app/page.tsx` | The page: stats and the architecture diagram on the left, the chat and its steps on the right. |
| `web/app/architecture.tsx` | The diagram: lights up each box the turn has passed through, and makes the current one glow. |
| `web/app/step.tsx` | How each event type is drawn as a row in the timeline. |
| `web/app/events.ts` | The event types (mirroring `tomu/events.py`) and `streamChat`, which reads the stream. |

## Checks

`uv run ruff check .` · `uv run pytest` · `cd web && npm run lint && npm run build`
