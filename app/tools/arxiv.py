from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import httpx

from app.db.cache import get_cached_response, make_cache_key, save_cached_response
from app.models.tool import Source, ToolResult

ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"

ARXIV_HEADERS = {
    "User-Agent": "TheRabbitHole/0.1 (https://github.com/Srijan1683/The-Rabbit-Hole)",
}

async def search_papers(query: str, limit: int = 5) -> ToolResult:
    cache_key = make_cache_key(
        api_name="arxiv",
        query=query,
        params={"type": "search", "limit": limit},
    )
    
    cached = await get_cached_response(cache_key)
    
    if cached:
        sources = [
            Source(
                url=item.get("url"),
                title=item["title"],
                provider="arxiv",
                source_type="paper",
                author=item.get("author"),
                published_at=None,
                summary=item.get("summary"),
            )
            for item in cached["results"]
        ]
        
        return ToolResult(
            tool_name="arxiv_search",
            results=cached["results"],
            sources=sources,
            summary=f"Found {len(cached['results'])} paper results for {query}.",
            cached=True,
        )
        
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    
    async with httpx.AsyncClient(timeout=10, headers=ARXIV_HEADERS) as client:
        response = await client.get(ARXIV_SEARCH_URL, params=params)
        response.raise_for_status()
        
    root = ET.fromstring(response.text)
    
    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    
    results = []
    
    for entry in root.findall("atom:entry", namespace):
        title = entry.findtext("atom:title", default="", namespaces=namespace).strip()
        summary = entry.findtext("atom:summary", default="", namespaces=namespace).strip()
        url = entry.findtext("atom:id", default="", namespaces=namespace)
        published = entry.findtext("atom:published", default="", namespaces=namespace)
        
        authors = [
            author.findtext("atom:name", default="", namespaces=namespace)
            for author in entry.findall("atom:author", namespace)
        ]
        
        categories = [
            category.attrib.get("term")
            for category in entry.findall("atom:category", namespace)
            if category.attrib.get("term")
        ]
        
        paper_id = url.rsplit("/", 1)[-1] if url else None
        author_text = ", ".join(authors[:3]) if authors else None
        
        results.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "published": published,
                "authors": authors,
                "author": author_text,
                "paper_id": paper_id,
                "categories": categories,
            }
        )
        
    cache_payload = {
        "query": query,
        "results": results,
    }
    
    await save_cached_response(
        cache_key=cache_key,
        api_name="arxiv",
        query=query,
        response_data=cache_payload,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    
    sources = [
        Source(
            title=item["title"],
            provider="arxiv",
            source_type="paper",
            url=item.get("url"),
            author=item.get("author"),
            published_at=None,
            summary=item.get("summary"),
        )
        for item in results
    ]
    
    return ToolResult(
        tool_name="arxiv_search",
        results=results,
        sources=sources,
        summary=f"Found {len(results)} paper results for {query}.",
        cached=False,
    )