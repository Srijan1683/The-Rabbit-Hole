from datetime import datetime
import hashlib
import json
from typing import Any

from .pool import get_pool


def _get_pool():
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool has not been initialised")
    return pool


def make_cache_key(api_name: str, query: str, params: dict[str, Any] | None = None) -> str:
    payload = {
        "api_name": api_name,
        "query": query.strip().lower(),
        "params": params or {},
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    pool = _get_pool()
    row = await pool.fetchrow(
        """SELECT response_data
        FROM cached_api_responses
        WHERE cache_key = $1
        AND expires_at > NOW()""",
        cache_key
    )
    return row["response_data"] if row else None


async def save_cached_response(
    cache_key: str,
    api_name: str,
    query: str,
    response_data: dict[str, Any],
    expires_at: datetime,
) -> None:
    pool = _get_pool()
    await pool.execute(
        """INSERT INTO cached_api_responses
        (cache_key, api_name, query, response_data, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (cache_key)
        DO UPDATE SET
            response_data = EXCLUDED.response_data,
            expires_at = EXCLUDED.expires_at,
            created_at = NOW()""",
        cache_key,
        api_name,
        query,
        response_data,
        expires_at,
    )
    

async def delete_expired_cache() -> int:
    pool = _get_pool()
    result = await pool.execute(
        "DELETE FROM cached_api_responses WHERE expires_at <= NOW()"
    )
    return int(result.split()[-1])