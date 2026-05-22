import json
import uuid
from typing import AsyncGenerator

from app.services.exploration import explore_topic

def format_sse_event(event: str, data: dict) -> dict:
    return {
        "event": event,
        "data": json.dumps(data, default=str),
    }
    
async def stream_exploration(
    query: str,
    session_id: uuid.UUID | None = None,
) -> AsyncGenerator[dict, None]:
    try:
        yield format_sse_event(
            "thinking",
            {
                "message": "Starting exploration",
                "query": query,
            },
        )

        result = await explore_topic(
            query=query,
            session_id=session_id,
        )

        yield format_sse_event(
            "content",
            {
                "response": result.response,
            },
        )

        yield format_sse_event(
            "sources",
            {
                "sources": [source.model_dump() for source in result.sources],
                "tool_calls": [tool_call.model_dump() for tool_call in result.tool_calls],
            },
        )

        yield format_sse_event(
            "done",
            {
                "session_id": str(result.session_id),
                "token_usage": result.token_usage.model_dump(),
            },
        )

    except Exception as exc:
        yield format_sse_event(
            "error",
            {
                "message": str(exc),
            },
        )