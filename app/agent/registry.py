from typing import Awaitable, Callable

from app.models.tool import ToolResult
from app.tools.arxiv import search_papers
from app.tools.open_library import search_books
from app.tools.podcast_index import search_podcasts
from app.tools.wikipedia import get_wikipedia_summary, search_wikipedia
from app.tools.youtube import search_videos


ToolFunction = Callable[..., Awaitable[ToolResult]]


TOOL_REGISTRY: dict[str, ToolFunction] = {
    "wikipedia_summary": get_wikipedia_summary,
    "wikipedia_search": search_wikipedia,
    "open_library_search": search_books,
    "arxiv_search": search_papers,
    "youtube_search": search_videos,
    "podcast_search": search_podcasts,
}


def get_tool_registry() -> dict[str, ToolFunction]:
    return TOOL_REGISTRY


def get_tool(name: str) -> ToolFunction:
    return TOOL_REGISTRY[name]


def list_tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())
