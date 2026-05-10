from .pool import get_pool
import uuid


def _get_pool():
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool has not been initialized")
    return pool


async def create_session(title=None):
    pool = _get_pool()
    row = await pool.fetchrow(
        "INSERT INTO sessions (title) VALUES ($1) RETURNING *",
        title
    )
    return dict(row)

async def get_session(session_id: uuid.UUID):
    pool = _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sessions WHERE session_id = $1",
        session_id
    )
    return dict(row) if row else None

async def list_sessions(limit: int = 20, offset: int = 0):
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT * FROM sessions ORDER BY last_active_at DESC LIMIT $1 OFFSET $2",
        limit, offset
    )
    total = await pool.fetchval("SELECT COUNT(*) FROM sessions")
    return [dict(r) for r in rows], total

async def delete_session(session_id: uuid.UUID):
    pool = _get_pool()
    result = await pool.execute(
        "DELETE FROM sessions WHERE session_id = $1",
        session_id
    )
    return result == "DELETE 1"

async def update_session_activity(session_id: uuid.UUID):
    pool = _get_pool()
    result = await pool.execute(
        """UPDATE sessions
        SET last_active_at = NOW(),
            message_count = message_count + 1
        WHERE session_id = $1""",
        session_id
    )
    return result == "UPDATE 1"
