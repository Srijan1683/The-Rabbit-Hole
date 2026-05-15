from datetime import datetime, timezone, timedelta

import httpx

from app.core.config import settings
from app.db.cache import get_cached_response, make_cache_key, save_cached_response
from app.models.tool import Source, ToolResult

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


async def search_videos(query: str, limit: int = 5) -> ToolResult:
    cache_key = make_cache_key(
        api_name="youtube",
        query=query,
        params={"type": "search", "limit": limit},
    )
    
    cached = await get_cached_response(cache_key)
    
    if cached:
        sources = [
            Source(
                url=item.get("url"),
                title=item["title"],
                provider="youtube",
                source_type="video",
                author=item.get("channel_title"),
                published_at=None,
                summary=item.get("summary"),
            )
            for item in cached["results"]
        ]
        
        
        return ToolResult(
            tool_name="youtube_search",
            results=cached["results"],
            sources=sources,
            summary=f"Found {len(cached['results'])} search results for {query}.",
            cached=True
        )
    
    if not settings.youtube_api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY")
    
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": limit,
        "key": settings.youtube_api_key,
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(YOUTUBE_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
    results = []
    
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        
        title = snippet.get("title")
        description = snippet.get("description")
        channel_title = snippet.get("channelTitle")
        published_at = snippet.get("publishedAt")
        thumbnail_url = snippet.get("thumbnails", {}).get("medium", {}).get("url")
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
        
        results.append(
            {
                "video_id": video_id,
                "title": title,
                "description": description,
                "channel_title": channel_title,
                "published_at": published_at,
                "thumbnail_url": thumbnail_url,
                "url": url,
                "summary": description,
            }
        )
    
    cache_payload = {
        "query": query,
        "results": results,
    }
    
    await save_cached_response(
        cache_key=cache_key,
        api_name="youtube",
        query=query,
        response_data=cache_payload,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
    )
    
    sources = [
        Source(
            title=item["title"],
            provider="youtube",
            source_type="video",
            url=item.get("url"),
            author=item.get("channel_title"),
            summary=item.get("summary"),
        )
        for item in results
    ]
    
    return ToolResult(
        tool_name="youtube_search",
        results=results,
        sources=sources,
        summary=f"Found {len(results)} search results for {query}.",
        cached=False,
    )