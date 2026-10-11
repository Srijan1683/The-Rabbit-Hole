from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from app.tools import wikipedia


@pytest.mark.asyncio
@respx.mock
async def test_wikipedia_summary_returns_and_caches_api_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached_response: dict[str, object] = {}

    async def no_cached_response(_: str) -> None:
        return None

    async def capture_cached_response(**kwargs: object) -> None:
        cached_response.update(kwargs)

    async def ignore_api_usage(**_: object) -> None:
        return None

    monkeypatch.setattr(wikipedia, "get_cached_response", no_cached_response)
    monkeypatch.setattr(wikipedia, "save_cached_response", capture_cached_response)
    monkeypatch.setattr(wikipedia, "save_api_usage", ignore_api_usage)
    monkeypatch.setattr(wikipedia, "update_rate_limit_from_headers", lambda *_: None)

    route = respx.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/Ada%20Lovelace"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "title": "Ada Lovelace",
                "extract": "English mathematician and writer.",
                "pageid": 123,
                "content_urls": {"desktop": {"page": "https://example.com/ada"}},
            },
        )
    )

    before_request = datetime.now(UTC)
    result = await wikipedia.get_wikipedia_summary("Ada Lovelace")

    assert route.called
    assert result.cached is False
    assert result.summary == "English mathematician and writer."
    assert result.sources[0].url == "https://example.com/ada"
    assert cached_response["response_data"] == result.results[0]
    assert cached_response["expires_at"] >= before_request + timedelta(hours=24)
