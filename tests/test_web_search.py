"""search_web asks Tavily for results and turns them into plain text for the model."""

import io
import json

import pytest

from tomu import web_search


def fake_urlopen(body, seen):
    def urlopen(request, timeout):
        seen.append(request)
        return io.BytesIO(json.dumps(body).encode())
    return urlopen


def test_search_web_sends_the_query_and_key_and_lists_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-123")
    seen = []
    results = [{"title": "London weather", "url": "https://example.com/london",
                "content": "Rain, 12°C"}]
    monkeypatch.setattr(web_search, "urlopen", fake_urlopen({"results": results}, seen))

    text = web_search.search_web("weather in London")

    assert text == "London weather\nhttps://example.com/london\nRain, 12°C"
    assert json.loads(seen[0].data) == {"query": "weather in London", "max_results": 5}
    assert seen[0].get_header("Authorization") == "Bearer tvly-123"


def test_search_web_says_when_nothing_was_found(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-123")
    monkeypatch.setattr(web_search, "urlopen", fake_urlopen({"results": []}, []))

    assert web_search.search_web("xyzzy") == "No results for 'xyzzy'."


def test_search_web_without_a_key_explains_how_to_set_it_up(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="add TAVILY_API_KEY to .env"):
        web_search.search_web("anything")
