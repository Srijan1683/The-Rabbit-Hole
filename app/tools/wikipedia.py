from datetime import datetime, timedelta, timezone
import httpx

from app.db.cache import get_cached_response, make_cache_key, save_cached_response
from app.models.tool import Source, ToolResult

WIKIPEDIA_HEADERS = {
    "User-Agent": "TheRabbitHole/0.1 (https://github.com/Srijan1683/The-Rabbit-Hole)",
    "Api-User-Agent": "TheRabbitHole/0.1 (https://github.com/Srijan1683/The-Rabbit-Hole)",
}


async def get_wikipedia_summary(query: str) -> ToolResult:
    cache_key = make_cache_key(
        api_name="wikipedia",
        query=query,
        params={"type": "summary"},
    )
    
    cached = await get_cached_response(cache_key)
    if cached:
        return ToolResult(
            tool_name="wikipedia",
            results=[cached],
            sources=[
                Source(
                    title=cached["title"],
                    provider="wikipedia",
                    source_type="article",
                    url=cached.get("url"),
                    summary=cached.get("summary"),
                )
            ],
            summary=cached.get("summary"),
            cached=True,
        )

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"

    async with httpx.AsyncClient(timeout=10, headers=WIKIPEDIA_HEADERS) as client:
        response = await client.get(url)
        if response.status_code == 404:
            return await search_wikipedia(query=query, limit=3)
        response.raise_for_status()
        data = response.json()

    result = {
        "title": data.get("title", query),
        "summary": data.get("extract"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        "page_id": data.get("pageid"),
    }

    await save_cached_response(
        cache_key=cache_key,
        api_name="wikipedia",
        query=query,
        response_data=result,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    source = Source(
        title=result["title"],
        provider="wikipedia",
        source_type="article",
        url=result.get("url"),
        summary=result.get("summary"),
    )

    return ToolResult(
        tool_name="wikipedia",
        results=[result],
        sources=[source],
        summary=result.get("summary"),
        cached=False,
    )


async def search_wikipedia(query: str, limit: int = 5) -> ToolResult:
    cache_key = make_cache_key(
        api_name="wikipedia",
        query=query,
        params={"type": "search", "limit": limit},
    )
    
    cached = await get_cached_response(cache_key)
    
    if cached:
        sources = [
            Source(
                title=item["title"],
                provider="wikipedia",
                source_type="article",
                url=item.get("url"),
                summary=item.get("snippet"),
            )
            for item in cached["results"]
        ]
        
        return ToolResult(
            tool_name="wikipedia_search",
            results=cached["results"],
            sources=sources,
            summary=f"Found {len(cached['results'])} Wikipedia results for {query}.",
            cached=True,
        )
        
    url = "https://en.wikipedia.org/w/api.php"
    
    params={
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": limit,
    }
    
    async with httpx.AsyncClient(timeout=10, headers=WIKIPEDIA_HEADERS) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
    results = []
    
    for item in data.get("query", {}).get("search", []):
        page_id = item["pageid"]
        title = item["title"]
        
        results.append(
            {
                "pageid": page_id,
                "title": title,
                "snippet": item.get("snippet"),
                "url": f"https://en.wikipedia.org/?curid={page_id}",
            }
        )
        
    cache_payload = {
        "query": query,
        "results": results,
    }
    
    await save_cached_response(
        cache_key=cache_key,
        api_name="wikipedia",
        query=query,
        response_data=cache_payload,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    sources = [
        Source(
            title=item["title"],
            provider="wikipedia",
            source_type="article",
            url=item["url"],
            summary=item.get("snippet"),
        )
        for item in results
    ]
    
    return ToolResult(
        tool_name="wikipedia_search",
        results=results,
        sources=sources,
        summary=f"Found {len(results)} Wikipedia results for {query}.",
        cached=False
    )
