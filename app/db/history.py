from .pool import get_pool
import uuid
from app.models.conversation import MessageRole

def _get_pool():
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool has not been initialized")
    return pool


async def save_message(session_id: uuid.UUID, role: MessageRole, content: str, token_count: int):
    pool = _get_pool()
    row = await pool.fetchrow(
        """INSERT INTO conversation_history
        (session_id, role, content, token_count)
        VALUES ($1, $2, $3, $4)
        RETURNING *""",
        session_id, role.value, content, token_count
    )
    await pool.execute(
        """UPDATE sessions
        SET last_active_at = NOW(),
            message_count = message_count + 1
        WHERE session_id = $1""",
        session_id
    )
    return dict(row)


async def get_history(session_id: uuid.UUID, limit: int = 50):
    pool = _get_pool()
    rows = await pool.fetch(
        """SELECT * FROM (
        SELECT * FROM conversation_history
        WHERE session_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        ) recent_messages
        ORDER BY created_at ASC""",
        session_id, limit
    )
    return [dict(r) for r in rows]
