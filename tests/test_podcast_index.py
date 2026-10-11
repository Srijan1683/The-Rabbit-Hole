import httpx
import pytest
import respx

from app.tools import podcast_index


@pytest.mark.asyncio
@respx.mock
async def test_podcast_index_search_uses_mocked_api_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_cached_response(_: str) -> None:
        return None

    async def ignore_side_effect(**_: object) -> None:
        return None

    monkeypatch.setattr(podcast_index, "get_cached_response", no_cached_response)
    monkeypatch.setattr(podcast_index, "save_cached_response", ignore_side_effect)
    monkeypatch.setattr(podcast_index, "save_api_usage", ignore_side_effect)
    monkeypatch.setattr(
        podcast_index,
        "update_rate_limit_from_headers",
        lambda *_: None,
    )
    monkeypatch.setattr(podcast_index, "_build_auth_headers", lambda: {"X-Test": "1"})

    route = respx.get(podcast_index.PODCAST_INDEX_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "feeds": [
                    {
                        "id": 42,
                        "title": "Science Friday",
                        "description": "Science news and stories.",
                        "author": "WNYC",
                        "link": "https://example.com/science-friday",
                        "url": "https://example.com/feed.xml",
                        "episodeCount": 99,
                    }
                ]
            },
        )
    )

    result = await podcast_index.search_podcasts("science")

    assert route.called
    assert result.cached is False
    assert result.results[0]["podcast_id"] == 42
    assert result.sources[0].author == "WNYC"
