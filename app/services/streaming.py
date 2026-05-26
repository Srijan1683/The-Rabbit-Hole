import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

import httpx

from app.agent.agent import (
    TOOL_API_NAMES,
    choose_tools_for_query,
    format_tool_results,
    get_openai_client,
)
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.rate_limiter import (
    calculate_backoff_seconds,
    is_rate_limited,
    mark_api_success,
    mark_rate_limited,
)
from app.agent.registry import get_tool
from app.agent.token_manager import (
    build_token_budget,
    count_messages_tokens,
    get_context_window,
    select_history_for_context,
)
from app.core.config import settings
from app.db.history import save_tool_call
from app.db.sessions import create_session, get_session
from app.models.conversation import MessageRole
from app.models.tool import Source, ToolResult
from app.services.exploration import build_history_context, collect_sources
from app.services.memory import count_tokens, load_session_history, store_message



def format_sse_event(event: str, data: dict) -> dict:
    return {
        "event": event,
        "data": json.dumps(data, default=str),
    }
    

def serialize_sources(sources: list[Source]) -> list[dict]:
    return [source.model_dump() for source in sources]


async def run_streaming_tools(
    query: str,
) -> AsyncGenerator[tuple[str, dict], None]:
    tool_names = choose_tools_for_query(query)
    tool_results: list[ToolResult] = []
    
    for tool_name in tool_names:
        api_name = TOOL_API_NAMES.get(tool_name, tool_name)
        
        if is_rate_limited(api_name):
            yield (
                "tool_result",
                {
                    "tool_name": tool_name,
                    "status": "skipped",
                    "reason": f"{api_name} is currently rate-limited"
                },
            )
            continue
        
        yield (
            "tool_call",
            {
                "tool_name": tool_name,
                "input": {"query": query},
            },
        )
        
        tool = get_tool(tool_name)
        started_at = time.perf_counter()
        
        for attempt in range(3):
            try:
                result = await tool(query=query)
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                
                mark_api_success(api_name)
                tool_results.append(result)
                
                yield (
                    "tool_result",
                    {
                        "tool_name": result.tool_name,
                        "status": "success",
                        "summary": result.summary,
                        "cached": result.cached,
                        "duration_ms": duration_ms,
                        "source_count": len(result.sources),
                    },
                )
                break
            
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    backoff_seconds = calculate_backoff_seconds(
                        api_name=api_name,
                        headers=exc.response.headers,
                    )
                    mark_rate_limited(api_name, cooldown_seconds=backoff_seconds)
                    
                    yield (
                        "tool_result",
                        {
                            "tool_name": tool_name,
                            "status": "rate_limited",
                            "retry_after_seconds": backoff_seconds,
                        },
                    )
                    
                    if attempt < 2:
                        await asyncio.sleep(backoff_seconds)
                        continue
                    
                yield (
                    "tool_result",
                    {
                        "tool_name": tool_name,
                        "status": "failed",
                        "error": str(exc),
                    },
                )
                break
            
            except Exception as exc:
                yield (
                    "tool_result",
                    {
                        "tool_name": tool_name,
                        "status": "failed",
                        "error": str(exc),
                    },
                )
                break
    yield ("_tool_results", {"tool_results": tool_results})
    
    
async def stream_model_response(
    query: str,
    context: str,
    tool_results: list[ToolResult],
) -> AsyncGenerator[str, None]:
    
    client = get_openai_client()
    tool_context = format_tool_results(tool_results)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    if context:
        messages.append({"role": "system", "content": context})
        
    if tool_context:
        messages.append({"role": "system", "content": tool_context})
        
    messages.append({"role": "user", "content": query})
    
    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content

        if delta:
            yield delta

    
async def stream_exploration(
    query: str,
    session_id: uuid.UUID | None = None,
) -> AsyncGenerator[dict, None]:
    try:
        yield format_sse_event(
            "thinking",
            {
                "message": "Preparing session and loading memory",
                "query": query,
            },
        )
        
        if session_id is None:
            session = await create_session(title=query[:80])
            session_id = session["session_id"]
        
        else:
            session = await get_session(session_id)
            
            if session is None:
                yield format_sse_event(
                    "error",
                    {"message": "Session not found"},
                )
                return
            
        history = await load_session_history(session_id=session_id)
        
        system_prompt_tokens = count_tokens(SYSTEM_PROMPT)
        current_query_tokens = count_tokens(query)
        context_window = get_context_window(settings.openai_model)
        
        response_reserve = 4096
        tool_output_reserve = 12000
        
        available_history_tokens = max(
            context_window
            - system_prompt_tokens
            - current_query_tokens
            - response_reserve
            - tool_output_reserve,
            0,
        )
        
        selected_history = select_history_for_context(
            messages=history,
            available_tokens=available_history_tokens,
            model=settings.openai_model,
        )
        
        context = build_history_context(selected_history)
        
        await store_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=query,
        )
        
        yield format_sse_event(
            "thinking",
            {
                "message": "Choosing and running tools",
                "session_id": str(session_id),
            },
        )
        
        tool_results: list[ToolResult] = []
        
        async for event_name, event_data in run_streaming_tools(query):
            if event_name == "_tool_results":
                tool_results = event_data["tool_results"]
                continue
            
            yield format_sse_event(event_name, event_data)
            
        for result in tool_results:
            await save_tool_call(
                session_id=session_id,
                tool_name=result.tool_name,
                input_args={"query": query},
                output_summary=result.summary,
                duration_ms=0,
                cached=result.cached,
            )
            
        yield format_sse_event(
            "thinking",
            {
                "message": "Generating response",
            },
        )
        
        response_parts: list[str] = []
        
        async for chunk in stream_model_response(
            query=query,
            context=context,
            tool_results=tool_results,
        ):
            response_parts.append(chunk)
            yield format_sse_event(
                "content",
                {
                    "delta": chunk,
                },
            )
            
        response_text = "".join(response_parts)
            
        await store_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )
        
        sources = collect_sources(tool_results)

        yield format_sse_event(
            "sources",
            {
                "sources": serialize_sources(sources),
            },
        )

        history_tokens = count_messages_tokens(
            selected_history,
            model=settings.openai_model,
        )

        token_usage = build_token_budget(
            model=settings.openai_model,
            context_window=context_window,
            system_prompt_tokens=system_prompt_tokens,
            current_query_tokens=current_query_tokens,
            history_tokens=history_tokens,
            response_reserve=response_reserve,
            history_messages_included=len(selected_history),
            history_messages_truncated=max(len(history) - len(selected_history), 0),
        )

        yield format_sse_event(
            "done",
            {
                "session_id": str(session_id),
                "token_usage": token_usage.model_dump(),
            },
        )

    except Exception as exc:
        yield format_sse_event(
            "error",
            {
                "message": str(exc),
            },
        )
