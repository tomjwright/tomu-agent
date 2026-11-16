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
token stays on your machine in `google-token.json`. The agent can read your calendar and email
freely, but adding an event or sending an email stops for your approval first: the
chat shows the exact inputs with Approve and Deny buttons, and the terminal asks `[y/N]`.
No answer within 5 minutes counts as no. If you signed in before approvals existed, run
`uv run tomu-google` again to grant the extra permissions.

To let it search the web, get a free Tavily API key at https://tavily.com and put it in
`.env` as `TAVILY_API_KEY`. Ask about something current, like the weather or
the news, and you'll see a `search_web` step with the links it found. For a bigger question,
the `web-research` skill tells it to search more than once and list its sources.

To chat from your phone, create a bot with @BotFather on Telegram (`/newbot`), put its
token in `.env` as `TELEGRAM_BOT_TOKEN`, and run `uv run tomu-telegram`. It answers only
`TELEGRAM_ALLOWED_USER`, your numeric Telegram user id: message the bot once and your id
is printed in the terminal. Approvals arrive as Approve and Deny buttons, and each reply
ends with a one-line summary of its steps. It shares memory with the page and terminal.

To check whether a change made Tomu better or worse, run `uv run tomu-evals`, or press
**Run evals** on the page. It sends every message in `evals/cases.json` to the model and
checks which tools it called and what the reply mentions, then prints a score like
`7/8 passed`. Each case uses a throwaway memory, and approvals are always answered no, so
nothing is sent or created. Add a case by adding an entry to that file.

Before relying on a change to the prompt, the model or a tool, run the release gate:
`uv run tomu-gate`, or press **Run release gate** on the page. It runs the tests first,
and if they all pass, the evals. The gate is OPEN (safe to release) only when every test
passes and at least 80% of the evals do; otherwise it's CLOSED. Each verdict is saved in
`tomu.db`, and the page lists recent ones.

The page sends its requests to its own `/api/...`, and Next.js passes them on to the API
on `localhost:8000` (set `TOMU_API` to point it somewhere else). So the browser only needs
to reach the page, which also makes it work through a remote preview.

Stream a turn's steps from the API:

```bash
curl -N -X POST localhost:8000/api/chat \
  -H 'content-type: application/json' -d '{"message":"what time is it in Tokyo?"}'
```

## How it works

| File | What it does |
|---|---|
| `tomu/loop.py` | The loop: call the model, run the tools it asks for (after your approval, for tools that change something), feed the results back, repeat. |
| `tomu/events.py` | The events a turn emits: `turn_start`, `memory_recall`, `llm_call`, `tool_call`, `approval_request`, `approval_result`, `tool_result`, `turn_end`, `memory_save`, `error`. |
| `tomu/tools.py` | The `Tool` type, the registry that runs tools, and the demo `get_current_time` tool. |
| `tomu/memory.py` | Memory in one SQLite file (`tomu.db`, or `TOMU_DB`): chat history, facts with full-text search, the retrieval gate, the `remember` tool, and the traces of past turns. |
| `tomu/consolidate.py` | Consolidation: every 20 new messages (or when you press Consolidate), the model turns old conversation into lasting facts. |
| `tomu/skills.py` | Skills (procedural memory): loads every `skills/<name>/SKILL.md`, and the `use_skill` tool the model calls to read one. |
| `skills/` | The skills themselves, as plain Markdown: a `name` and `description` header, then instructions for the model. |
| `tomu/google_auth.py` | `uv run tomu-google`, which signs you in to Google, and the shared login the Google tools use. |
| `tomu/google_calendar.py` | `list_calendar_events`, and `create_calendar_event`, which needs your approval. |
| `tomu/web_search.py` | `search_web`: searches the web with the Tavily Search API and returns titles, links and snippets. |
| `tomu/gmail.py` | `search_email` and `read_email`, and `send_email`, which needs your approval. |
| `tomu/agent.py` | `run_agent(message, emit)`: loads memory, wires the Anthropic client, system prompt and tools into the loop, then saves the turn. |
| `tomu/server.py` | `POST /api/chat`: runs a turn and streams its events as Server-Sent Events. `POST /api/approve` answers an approval request. `GET /api/traces` and `GET /api/traces/{id}` return past turns for replay. `POST /api/evals` runs the evals and streams one result per case. `POST /api/gate` runs the release gate, and `GET /api/gate` lists past verdicts. |
| `tomu/evals.py` | `uv run tomu-evals`: runs every case in `evals/cases.json` with a throwaway memory and checks what the model decided. |
| `tomu/gate.py` | `uv run tomu-gate`: the release gate. Runs the tests, then the evals, and saves an OPEN or CLOSED verdict. |
| `evals/cases.json` | The eval cases: a message, plus the tools it should call (`tools`), `no_tools`, words the reply should mention (`reply`) and facts to preload (`facts`). |
| `tomu/cli.py` | The terminal chat. |
| `tomu/telegram.py` | `uv run tomu-telegram`: the Telegram gateway, with approval buttons. |
| `web/app/page.tsx` | The page: stats and the architecture diagram on the left, the chat and its steps on the right. |
| `web/app/architecture.tsx` | The diagram: lights up each box the turn has passed through, and makes the current one glow. |
| `web/app/step.tsx` | How each event type is drawn as a row in the timeline. |
| `web/app/events.ts` | The event types (mirroring `tomu/events.py`) `streamChat`, which reads the stream, and `answerApproval`. |

## Checks

`uv run ruff check .` · `uv run pytest` · `cd web && npm run lint && npm run build`
