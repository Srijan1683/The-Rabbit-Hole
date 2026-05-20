import uuid

from app.agent.agent import run_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.token_manager import build_token_budget, get_context_window
from app.core.config import settings
from app.db.sessions import create_session, get_session
from app.models.conversation import ExploreResponse, MessageRole
from app.services.memory import count_tokens, load_session_history, store_message

def build_history_context(history: list[dict]) -> str:
    if not history:
        return ""
    
    lines = ["Previous conversation:"]
    
    for message in history:
        role = message["role"]
        content = message["content"]
        lines.append(f"{role}: {content}")
        
    return "\n".join(lines)


async def explore_topic(
    query: str,
    session_id: uuid.UUID | None = None,
) -> ExploreResponse:
    
    if session_id is None:
        session = await create_session(title=query[:80])
        session_id = session["session_id"]
        
    else:
        session = await get_session(session_id)
        
        if session is None:
            raise ValueError("Session not found")
        
    history = await load_session_history(session_id=session_id)
    context = build_history_context(history)
    
    await store_message(
        session_id=session_id,
        role=MessageRole.USER,
        content=query,
    )
    
    response_text = await run_agent(query=query, context=context)
    
    await store_message(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=response_text,
    )
    
    system_prompt_tokens = count_tokens(SYSTEM_PROMPT)
    current_query_tokens = count_tokens(query)
    history_tokens = count_tokens(context)
    context_window = get_context_window(settings.openai_model)
    
    token_usage = build_token_budget(
        model=settings.openai_model,
        context_window=context_window,
        system_prompt_tokens=system_prompt_tokens,
        current_query_tokens=current_query_tokens,
        history_tokens=history_tokens,
        history_messages_included=len(history),
        history_messages_truncated=0,
    )
    
    return ExploreResponse(
        session_id=session_id,
        response=response_text,
        sources=[],
        tool_calls=[],
        token_usage=token_usage,
    )
