# AGENTS.md: read this before every change

Rules for anyone changing this repo, human or coding agent.

## The project

Tomu is a local AI agent that shows every step it takes to reach an answer.
The goal is code that is easy to read: the agent, tools, memory and
integrations are written in **Python**; Next.js is used only for the frontend.

## How we work

1. **Always work on a feature branch.** Cut it from an up-to-date `main`.
   Never commit or push to `main`; it only changes through merged PRs.
2. **Keep PRs small.** One feature or idea per PR, roughly 200-300 lines of
   hand-written code. Don't stack a PR on another open PR's branch.
3. **Explain PRs in plain English.** The description says what changed and why,
   walks through each file in a sentence or two, and gives a concrete example.
4. **Test before committing and before opening a PR.** Run the checks below and
   run the code you changed (the CLI, the API, or the page). If something could
   not be tested, say so in the PR.
5. **Clean up after a merge.** Delete the feature branch (remote and local) and
   switch back to an up-to-date `main`.

## Checks

```bash
uv run ruff check .
uv run pytest
```
