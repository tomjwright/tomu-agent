"""Web search: lets the agent look things up on the web with the Brave Search API.

Get a free key at https://brave.com/search/api/ and put it in .env as BRAVE_API_KEY.
It only reads, so it doesn't need your approval.
"""

import json
import os
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tomu.tools import Tool

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def search_web(query: str, count: int = 5) -> str:
    key = os.getenv("BRAVE_API_KEY")
    if not key:
        raise RuntimeError("web search isn't set up: add BRAVE_API_KEY to .env")
    request = Request(f"{SEARCH_URL}?{urlencode({'q': query, 'count': count})}",
                      headers={"Accept": "application/json", "X-Subscription-Token": key})
    with urlopen(request, timeout=10) as response:
        results = json.load(response).get("web", {}).get("results", [])
    if not results:
        return f"No results for {query!r}."
    return "\n\n".join(describe(result) for result in results)


def describe(result: dict) -> str:
    """One result as three lines: title, link, and the snippet without Brave's <strong> tags."""
    snippet = re.sub(r"<[^>]+>", "", result.get("description", ""))
    return f"{result['title']}\n{result['url']}\n{snippet}"


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
