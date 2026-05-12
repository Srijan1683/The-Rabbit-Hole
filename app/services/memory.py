import uuid
import tiktoken

from app.core.config import settings
from app.db.history import get_history, save_message
from app.models.conversation import MessageRole

def count_tokens(text: str, model: str | None = None) -> int:
    model_name = model or settings.openai_model
    
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
        
    return len(encoding.encode(text))


async def store_message(
    session_id: uuid.UUID,
    role: MessageRole,
    content: str,
) -> dict:
    token_count = count_tokens(content)
    return await save_message(
        session_id=session_id,
        role=role,
        content=content,
        token_count=token_count,
    )
    
async def load_session_history(session_id: uuid.UUID, limit: int = 50) -> list[dict]:
    return await get_history(session_id=session_id, limit=limit)
