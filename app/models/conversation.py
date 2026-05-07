from typing import Literal

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    message_id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    token_count: int
    created_at: datetime

class ExploreRequest(BaseModel):
    session_id: UUID | None = None  # None = create new session
    query: str

class ToolCallRecord(BaseModel):
    tool_name: str
    input_args: dict
    output_summary: str
    duration_ms: int
    cached: bool

class Source(BaseModel):
    title: str
    url: str
    source_type: Literal["wikipedia", "book", "paper", "podcast", "video"]
    relevance: str  # brief note on why this was included

class ExploreResponse(BaseModel):
    session_id: UUID
    response: str
    sources: list[Source]
    tool_calls: list[ToolCallRecord]
    token_usage: TokenBudget