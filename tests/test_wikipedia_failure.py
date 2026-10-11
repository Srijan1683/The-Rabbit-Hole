import httpx
import pytest
import respx

from app.tools import wikipedia


@pytest.mark.asyncio
@respx.mock
async def test_wikipedia_summary_raises_for_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_cached_response(_: str) -> None:
        return None

    async def ignore_api_usage(**_: object) -> None:
        return None

    monkeypatch.setattr(wikipedia, "get_cached_response", no_cached_response)
    monkeypatch.setattr(wikipedia, "save_api_usage", ignore_api_usage)
    monkeypatch.setattr(wikipedia, "update_rate_limit_from_headers", lambda *_: None)

    route = respx.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/Ada%20Lovelace"
    ).mock(return_value=httpx.Response(500, text="Wikipedia is unavailable"))

    with pytest.raises(httpx.HTTPStatusError):
        await wikipedia.get_wikipedia_summary("Ada Lovelace")

    assert route.called
