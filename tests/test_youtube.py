from types import SimpleNamespace

import httpx
import pytest
import respx

from app.tools import youtube


@pytest.mark.asyncio
@respx.mock
async def test_youtube_search_uses_mocked_api_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_cached_response(_: str) -> None:
        return None

    async def ignore_side_effect(**_: object) -> None:
        return None

    monkeypatch.setattr(youtube, "get_cached_response", no_cached_response)
    monkeypatch.setattr(youtube, "save_cached_response", ignore_side_effect)
    monkeypatch.setattr(youtube, "save_api_usage", ignore_side_effect)
    monkeypatch.setattr(youtube, "update_rate_limit_from_headers", lambda *_: None)
    monkeypatch.setattr(youtube, "settings", SimpleNamespace(youtube_api_key="test-key"))

    route = respx.get(youtube.YOUTUBE_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": {"videoId": "abc123"},
                        "snippet": {
                            "title": "Quantum &amp; Physics",
                            "description": "An &amp; introduction.",
                            "channelTitle": "Science &amp; More",
                            "publishedAt": "2025-01-01T00:00:00Z",
                            "thumbnails": {"medium": {"url": "https://example.com/thumb"}},
                        },
                    }
                ]
            },
        )
    )

    result = await youtube.search_videos("quantum physics")

    assert route.called
    assert result.cached is False
    assert result.results[0]["title"] == "Quantum & Physics"
    assert result.sources[0].url == "https://www.youtube.com/watch?v=abc123"
