from enum import Enum

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.models.token import TokenBudget
from app.models.tool import Source


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
    session_id: UUID | None = None
    query: str

class ToolCallRecord(BaseModel):
    tool_name: str
    input_args: dict
    output_summary: str
    duration_ms: int
    cached: bool

class ExploreResponse(BaseModel):
    session_id: UUID
    response: str
    sources: list[Source]
    tool_calls: list[ToolCallRecord]
    token_usage: TokenBudget
