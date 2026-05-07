from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SourceProvider = Literal[
    "wikipedia",
    "open_library",
    "arxiv",
    "podcast_index",
    "youtube",
]

SourceType = Literal[
    "article",
    "book",
    "paper",
    "podcast",
    "video",
    "web",
]


class Source(BaseModel):
    title: str
    provider: SourceProvider
    source_type: SourceType
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    summary: str | None = None


class ToolCall(BaseModel):
    tool_name: str
    input_args: dict[str, Any]


class ToolResult(BaseModel):
    tool_name: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    summary: str | None = None
    cached: bool = False


class ToolCallLog(BaseModel):
    id: UUID
    session_id: UUID
    message_id: UUID | None = None
    tool_name: str
    input_args: dict[str, Any]
    output_summary: str | None = None
    duration_ms: int | None = None
    cached: bool
    called_at: datetime


class CachedApiResponse(BaseModel):
    cache_key: str
    api_name: SourceProvider
    query: str
    response_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime
