import pytest

from app.db import cache


class FakePool:
    def __init__(self) -> None:
        self.query = ""
        self.cache_key = ""

    async def fetchrow(self, query: str, cache_key: str) -> None:
        self.query = query
        self.cache_key = cache_key


@pytest.mark.asyncio
async def test_cache_lookup_only_returns_unexpired_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = FakePool()
    monkeypatch.setattr(cache, "get_pool", lambda: pool)

    result = await cache.get_cached_response("example-key")

    assert result is None
    assert pool.cache_key == "example-key"
    assert "expires_at > NOW()" in pool.query
