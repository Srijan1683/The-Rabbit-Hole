import httpx
import pytest
import respx

from app.tools import open_library


@pytest.mark.asyncio
@respx.mock
async def test_open_library_search_uses_mocked_api_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_cached_response(_: str) -> None:
        return None

    async def ignore_side_effect(**_: object) -> None:
        return None

    monkeypatch.setattr(open_library, "get_cached_response", no_cached_response)
    monkeypatch.setattr(open_library, "save_cached_response", ignore_side_effect)
    monkeypatch.setattr(open_library, "save_api_usage", ignore_side_effect)
    monkeypatch.setattr(open_library, "update_rate_limit_from_headers", lambda *_: None)

    route = respx.get(open_library.OPEN_LIBRARY_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "docs": [
                    {
                        "title": "Frankenstein",
                        "author_name": ["Mary Shelley"],
                        "first_publish_year": 1818,
                        "key": "/works/OL450063W",
                    }
                ]
            },
        )
    )

    result = await open_library.search_books("Frankenstein")

    assert route.called
    assert result.cached is False
    assert result.results[0]["author"] == "Mary Shelley"
    assert result.sources[0].url == "https://openlibrary.org/works/OL450063W"
