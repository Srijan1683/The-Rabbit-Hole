import httpx
import pytest
import respx

from app.tools import arxiv


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_search_uses_mocked_api_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_cached_response(_: str) -> None:
        return None

    async def ignore_side_effect(**_: object) -> None:
        return None

    monkeypatch.setattr(arxiv, "get_cached_response", no_cached_response)
    monkeypatch.setattr(arxiv, "save_cached_response", ignore_side_effect)
    monkeypatch.setattr(arxiv, "save_api_usage", ignore_side_effect)
    monkeypatch.setattr(arxiv, "update_rate_limit_from_headers", lambda *_: None)

    route = respx.get(arxiv.ARXIV_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            text="""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <feed xmlns=\"http://www.w3.org/2005/Atom\">
              <entry>
                <id>http://arxiv.org/abs/1234.5678</id>
                <title>Quantum Entanglement</title>
                <summary>A paper about entanglement.</summary>
                <published>2025-01-01T00:00:00Z</published>
                <author><name>Ada Lovelace</name></author>
                <category term=\"quant-ph\" />
              </entry>
            </feed>""",
        )
    )

    result = await arxiv.search_papers("quantum entanglement")

    assert route.called
    assert result.cached is False
    assert result.results[0]["paper_id"] == "1234.5678"
    assert result.sources[0].author == "Ada Lovelace"
