from datetime import datetime, timedelta, timezone
import hashlib
import time

import httpx

from app.core.config import settings
from app.db.cache import get_cached_response, make_cache_key, save_cached_response
from app.models.tool import Source, ToolResult


PODCAST_INDEX_SEARCH_URL = "https://api.podcastindex.org/api/1.0/search/byterm"


def _build_auth_headers() -> dict[str, str]:
    if not settings.podcast_index_api_key:
        raise RuntimeError("Missing PODCAST_INDEX_API_KEY")

    if not settings.podcast_index_api_secret:
        raise RuntimeError("Missing PODCAST_INDEX_API_SECRET")

    auth_date = str(int(time.time()))
    auth_string = (
        settings.podcast_index_api_key
        + settings.podcast_index_api_secret
        + auth_date
    )
    authorization = hashlib.sha1(auth_string.encode()).hexdigest()

    return {
        "User-Agent": "TheRabbitHole/0.1 (https://github.com/Srijan1683/The-Rabbit-Hole)",
        "X-Auth-Date": auth_date,
        "X-Auth-Key": settings.podcast_index_api_key,
        "Authorization": authorization,
    }


async def search_podcasts(query: str, limit: int = 5) -> ToolResult:
    cache_key = make_cache_key(
        api_name="podcast_index",
        query=query,
        params={"type": "search", "limit": limit},
    )

    cached = await get_cached_response(cache_key)

    if cached:
        sources = [
            Source(
                title=item["title"],
                provider="podcast_index",
                source_type="podcast",
                url=item.get("url") or item.get("feed_url"),
                author=item.get("author"),
                summary=item.get("summary"),
            )
            for item in cached["results"]
        ]

        return ToolResult(
            tool_name="podcast_index_search",
            results=cached["results"],
            sources=sources,
            summary=f"Found {len(cached['results'])} podcast results for {query}.",
            cached=True,
        )

    params = {
        "q": query,
        "max": limit,
        "clean": True,
    }

    async with httpx.AsyncClient(timeout=10, headers=_build_auth_headers()) as client:
        response = await client.get(PODCAST_INDEX_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    results = []

    for item in data.get("feeds", []):
        title = item.get("title")

        if not title:
            continue

        podcast_id = item.get("id")
        description = item.get("description")
        author = item.get("author")
        url = item.get("link")
        feed_url = item.get("url")
        image = item.get("image")
        episode_count = item.get("episodeCount")

        results.append(
            {
                "podcast_id": podcast_id,
                "title": title,
                "description": description,
                "author": author,
                "url": url,
                "feed_url": feed_url,
                "image": image,
                "episode_count": episode_count,
                "summary": description,
            }
        )

    cache_payload = {
        "query": query,
        "results": results,
    }

    await save_cached_response(
        cache_key=cache_key,
        api_name="podcast_index",
        query=query,
        response_data=cache_payload,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
    )

    sources = [
        Source(
            title=item["title"],
            provider="podcast_index",
            source_type="podcast",
            url=item.get("url") or item.get("feed_url"),
            author=item.get("author"),
            summary=item.get("summary"),
        )
        for item in results
    ]

    return ToolResult(
        tool_name="podcast_index_search",
        results=results,
        sources=sources,
        summary=f"Found {len(results)} podcast results for {query}.",
        cached=False,
    )
