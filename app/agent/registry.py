from dataclasses import dataclass
from typing import Awaitable, Callable

from app.models.tool import ToolResult
from app.tools.arxiv import search_papers
from app.tools.open_library import search_books
from app.tools.podcast_index import search_podcasts
from app.tools.wikipedia import get_wikipedia_summary, search_wikipedia
from app.tools.youtube import search_videos


ToolFunction = Callable[..., Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    api_name: str
    function: ToolFunction
    description: str
    best_for: str
    keywords: tuple[str, ...]
    
TOOL_SPECS: dict[str, ToolSpec] = {
    "wikipedia_summary": ToolSpec(
        name="wikipedia_summary",
        api_name="wikipedia",
        function=get_wikipedia_summary,
        description="Fetches a concise Wikipedia summary for a specific topic.",
        best_for="core definitions, background, historical context, notable people, places, concepts",
        keywords=("what is", "who is", "history", "meaning", "overview", "explain"),
    ),
    "wikipedia_search": ToolSpec(
        name="wikipedia_search",
        api_name="wikipedia",
        function=search_wikipedia,
        description="Searches Wikipedia for related articles and entities.",
        best_for="finding connected topics, related people, events, concepts, and broad article matches",
        keywords=("related", "connections", "topics", "articles", "search"),
    ),
    "open_library_search": ToolSpec(
        name="open_library_search",
        api_name="open_library",
        function=search_books,
        description="Searches Open Library for books and authors.",
        best_for="reading recommendations, books, authors, biographies, novels, nonfiction",
        keywords=("book", "books", "read", "author", "novel", "biography", "literature"),
    ),
    "arxiv_search": ToolSpec(
        name="arxiv_search",
        api_name="arxiv",
        function=search_papers,
        description="Searches arXiv for research papers and technical abstracts.",
        best_for="science, math, AI, physics, technical research, academic papers",
        keywords=("research", "paper", "study", "science", "technical", "physics", "math", "ai")
    ),
    "youtube_search": ToolSpec(
        name="youtube_search",
        api_name="youtube",
        function=search_videos,
        description="Searches Youtube for videos, talks, lectures, explainers, and documentaries.",
        best_for="visual explanations, lectures, talks, interviews, documentaries",
        keywords=("video", "watch", "youtube", "lecture", "documentary", "talk", "interview")
    ),
    "podcast_search": ToolSpec(
        name="podcast_search",
        api_name="podcast_index",
        function=search_podcasts,
        description="Searches Podcast Index for podcast/audio results.",
        best_for="podcasts, audio episodes, interviews, long-form listening",
        keywords=("podcast", "listen", "audio", "episode", "interview"),
    ),
}

TOOL_REGISTRY: dict[str, ToolFunction] = {
    name: spec.function
    for name, spec in TOOL_SPECS.items()
}

def get_tool_registry() -> dict[str, ToolFunction]:
    return TOOL_REGISTRY


def get_tool(name: str) -> ToolFunction:
    return TOOL_REGISTRY[name]


def get_tool_spec(name: str) -> ToolSpec:
    return TOOL_SPECS[name]


def list_tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())


def list_tool_specs() -> list[ToolSpec]:
    return list(TOOL_SPECS.values())


def format_tool_catalog() -> str:
    lines = []
    
    for spec in list_tool_specs():
        lines.append(
            f"- {spec.name}: {spec.description} Best for: {spec.best_for}."
        )
        
    return "\n".join(lines)
