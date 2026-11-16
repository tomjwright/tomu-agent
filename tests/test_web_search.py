"""search_web asks Brave for results and turns them into plain text for the model."""

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
    monkeypatch.setenv("BRAVE_API_KEY", "key-123")
    seen = []
    results = [{"title": "London weather", "url": "https://example.com/london",
                "description": "Rain, <strong>12°C</strong>"}]
    monkeypatch.setattr(web_search, "urlopen", fake_urlopen({"web": {"results": results}}, seen))

    text = web_search.search_web("weather in London")

    assert text == "London weather\nhttps://example.com/london\nRain, 12°C"
    assert "q=weather+in+London" in seen[0].full_url
    assert seen[0].get_header("X-subscription-token") == "key-123"


def test_search_web_says_when_nothing_was_found(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "key-123")
    monkeypatch.setattr(web_search, "urlopen", fake_urlopen({}, []))

    assert web_search.search_web("xyzzy") == "No results for 'xyzzy'."


def test_search_web_without_a_key_explains_how_to_set_it_up(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="add BRAVE_API_KEY to .env"):
        web_search.search_web("anything")
