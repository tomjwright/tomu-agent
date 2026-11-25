"""Web search: lets the agent look things up on the web with the Tavily Search API.

Get a free key at https://tavily.com and put it in .env as TAVILY_API_KEY.
It only reads, so it doesn't need your approval.
"""

import json
import os
from urllib.request import Request, urlopen

from tomu.tools import Tool

SEARCH_URL = "https://api.tavily.com/search"


def search_web(query: str, count: int = 5) -> str:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("web search isn't set up: add TAVILY_API_KEY to .env")
    request = Request(
        SEARCH_URL,
        data=json.dumps({"query": query, "max_results": count}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=20) as response:
        results = json.load(response).get("results", [])
    if not results:
        return f"No results for {query!r}."
    return "\n\n".join(f"{r['title']}\n{r['url']}\n{r.get('content', '')}" for r in results)


search_web_tool = Tool(
    name="search_web",
    description="Search the web for current or public information you don't know: news, "
    "weather, prices, opening hours, people, places. Returns titles, links and "
    "snippets.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for, as you'd type it."},
            "count": {"type": "integer", "description": "How many results. Default 5."},
        },
        "required": ["query"],
    },
    run=search_web,
)
