from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class TokenBudget(BaseModel):
    model: str
    context_window: int
    system_prompt: int
    conversation_history: int
    current_query: int
    available_for_response: int
    history_messages_included: int
    history_messages_truncated: int
    
class RateLimitStatus(BaseModel):
    api_name: str
    rate_limit_remaining: int | None = None
    rate_limit_reset_at: datetime | None = None
    is_throttled: bool
    
class APIUsageRecord(BaseModel):
    id: UUID
    api_name: str
    endpoint: str
    status_code: int
    response_time_ms: int | None = None
    called_at: datetime
    rate_limit_remaining: int | None = None
    rate_limit_reset_at: datetime | None = None