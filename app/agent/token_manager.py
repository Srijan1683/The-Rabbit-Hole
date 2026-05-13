from typing import Any

import tiktoken

from app.core.config import settings
from app.models.token import TokenBudget


def build_token_budget(
    model: str,
    context_window: int,
    system_prompt_tokens: int,
    current_query_tokens: int,
    history_tokens: int,
    response_reserve: int = 2000,
    history_messages_included: int = 0,
    history_messages_truncated: int = 0,
) -> TokenBudget:
    used_tokens = system_prompt_tokens + current_query_tokens + history_tokens
    available_for_response = max(context_window - used_tokens, 0)
    
    return TokenBudget(
        model=model,
        context_window=context_window,
        system_prompt=system_prompt_tokens,
        conversation_history=history_tokens,
        current_query=current_query_tokens,
        available_for_response=max(available_for_response - response_reserve, 0),
        history_messages_included=history_messages_included,
        history_messages_truncated=history_messages_truncated,
    ) 

def get_context_window(model: str | None = None) -> int:
    model_name = model or settings.openai_model
    
    context_window = {
        "openai/gpt-4o-mini": 128_000,
        "openai/gpt-4o": 128_000,
        "gpt-4o-mini": 128_000,
        "gpt-4o": 128_000,
    }
    
    return context_window.get(model_name, 128_000)

def count_message_tokens(message: dict[str, Any], model: str | None = None) -> int:
    model_name = model or settings.openai_model
    
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
        
    role = str(message.get("role", ""))
    content = str(message.get("content", ""))
    
    return len(encoding.encode(role)) + len(encoding.encode(content))


def count_messages_tokens(messages: list[dict[str, Any]], model: str | None = None) -> int:
    return sum(count_message_tokens(message, model=model) for message in messages)


def select_history_for_context(
    messages: list[dict[str, Any]],
    available_tokens: int,
    model: str | None = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used_tokens = 0
    
    for message in reversed(messages):
        message_tokens = count_message_tokens(message, model=model)
        
        if used_tokens + message_tokens > available_tokens:
            break
        
        selected.append(message)
        used_tokens += message_tokens
        
    return list(reversed(selected))


def truncate_text_to_tokens(
    text: str,
    max_tokens: int,
    model: str | None = None,
) -> str:
    model_name = model or settings.openai_model
    
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
        
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    return encoding.decode(tokens[:max_tokens])