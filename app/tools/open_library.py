from datetime import datetime, timedelta, timezone

import httpx

from app.db.cache import get_cached_response, make_cache_key, save_cached_response
from app.models.tool import Source, ToolResult


OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


async def search_books(query: str, limit: int = 5) -> ToolResult:
    cache_key = make_cache_key(
        api_name="open_library",
        query=query,
        params={"type": "search", "limit": limit},
    )
    
    cached = await get_cached_response(cache_key)
    
    if cached:
        sources = [
            Source(
                title=item["title"],
                provider="open_library",
                source_type="book",
                url=item.get("url"),
                author=item.get("author"),
                published_at=None,
                summary=item.get("summary"),
            )
            for item in cached["results"]
        ]
        
        return ToolResult(
            tool_name="open_library_search",
            results=cached["results"],
            sources=sources,
            summary=f"Found {len(cached['results'])} book results for {query}.",
            cached=True,
        )
    
    params = {
        "q": query,
        "limit": limit,
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
    results = []
    
    for item in data.get("docs", []):
        title = item.get("title")
        author_names = item.get("author_name", [])
        first_publish_year = item.get("first_publish_year")
        open_library_key = item.get("key")
        
        if not title:
            continue
        
        author = ", ".join(author_names[:3]) if author_names else None
        url = f"https://openlibrary.org{open_library_key}" if open_library_key else None
        
        results.append(
            {
                "title": title,
                "author": author,
                "first_publish_year": first_publish_year,
                "url": url,
                "open_library_key": open_library_key,
                "summary": (
                    f"{title}"
                    + (f" by {author}" if author else "")
                    +(f", first published in {first_publish_year}." if first_publish_year else ".")
                ),
            }
        )
        
    cache_payload = {
        "query": query,
        "results": results
    }
    
    await save_cached_response(
        cache_key=cache_key,
        api_name="open_library",
        query=query,
        response_data=cache_payload,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    
    sources = [
        Source(
            title=item["title"],
            provider="open_library",
            source_type="book",
            url=item.get("url"),
            author=item.get("author"),
            published_at=None,
            summary=item.get("summary"),
        )
        for item in results
    ]
    
    return ToolResult(
        tool_name="open_library_search",
        results=results,
        sources=sources,
        summary=f"Found {len(results)} book results for {query}.",
        cached=False,
    )