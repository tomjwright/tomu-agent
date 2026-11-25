# AGENTS.md: read this before every change

Rules for anyone changing this repo, human or coding agent.

## The project

Tomu is a local AI agent that shows every step it takes to reach an answer.
The goal is code that is easy to read: the agent, tools, memory and
integrations are written in **Python**; Next.js is used only for the frontend.

## Standards

The workflow rules shared by all of Tom's repos (branches, PR size and
descriptions, testing before a PR, clean-up after a merge) live in his home
repo, `tomjwright/home`. Rules for this repo:

- Python for the agent, tools, memory and integrations. Next.js only for the
  frontend.

## Checks

```bash
uv sync --all-extras    # the google extra is needed for mypy
uv run ruff check .
uv run mypy
uv run pytest
cd web && npm run lint && npm run build    # when the frontend changed
```
