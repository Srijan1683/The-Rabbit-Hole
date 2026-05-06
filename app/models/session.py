from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Session(BaseModel):
    session_id: UUID
    created_at: datetime
    last_active_at: datetime
    title: str | None = None
    message_count: int
    
class SessionCreate(BaseModel):
    title: str | None = None
    
class SessionList(BaseModel):
    sessions: list[Session]
    total: int