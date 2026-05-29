import asyncio
import html
import json
import re

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.agent.prompts import SYSTEM_PROMPT

from app.agent.rate_limiter import (
    calculate_backoff_seconds,
    is_rate_limited,
    mark_api_success,
    mark_rate_limited,
)

from app.agent.registry import format_tool_catalog, get_tool, list_tool_specs
from app.models.tool import ToolResult
from app.core.logging import get_logger
from app.agent.token_manager import truncate_text_to_tokens

TOOL_API_NAMES = {
    spec.name: spec.api_name
    for spec in list_tool_specs()
}

logger = get_logger(__name__)


def clean_source_text(value: str | None) -> str:
    if not value:
        return ""

    return html.unescape(value).strip()


def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

def choose_tools_for_query(query: str) -> list[str]:
    query_lower = query.lower()
    selected = ["wikipedia_summary", "wikipedia_search"]
    
    for spec in list_tool_specs():
        if spec.name in selected:
            continue
        
        if any(keyword in query_lower for keyword in spec.keywords):
            selected.append(spec.name)
        
    return selected


def _extract_json_array(text: str) -> list[str]:
    try:
        parsed = json.loads(text)
        
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        
    except json.JSONDecodeError:
        pass
    
    match = re.search(r"\[[\s\S]*\]", text)
    
    if not match:
        return []
    
    try:
        parsed = json.loads(match.group(0))
        
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        
    except json.JSONDecodeError:
        return []
    
    return []


async def choose_tools_with_model(query: str, context: str | None = None) -> list[str]:
    client = get_openai_client()
    tool_catalog = format_tool_catalog()
    allowed_tools = set(TOOL_API_NAMES)
    
    prompt = f"""
Choose the best tools for this user query.

User query:
{query}

Conversation context:
{context or "No previous context."}

Available tools:
{tool_catalog}

Rules:
- Always include wikipedia_summary for general grounding.
- Include wikipedia_search when connected concepts or related entities may help.
- Include open_library_search only when books/authors/reading would help.
- Include arxiv_search only for scientific, technical, mathematical, or research-heavy topics.
- Include youtube_search only when videos, lectures, talks, interviews, documentaries, or visual learning would help.
- Include podcast_search only when podcasts/audio/listening would help.
- Do not include every tool automatically.
- Return only a JSON array of tool names. No explanation.

Example:
["wikipedia_summary", "arxiv_search"]
"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You choose tools for research agent. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        
        content = response.choices[0].message.content or ""
        chosen_tools = _extract_json_array(content)
        
        valid_tools = [
            tool_name
            for tool_name in chosen_tools
            if tool_name in allowed_tools
        ]
        
        if valid_tools:
            if "wikipedia_summary" not in valid_tools:
                valid_tools.insert(0, "wikipedia_summary")
                
            return list(dict.fromkeys(valid_tools))
        
    except Exception:
        logger.exception("Model tool selection failed. Falling back to keyword selection.")
        
    return choose_tools_for_query(query)


async def resolve_tool_query(query: str, context: str | None = None) -> str:
    if not context:
        return query

    client = get_openai_client()

    prompt = f"""
Rewrite the user's request into a concise external search query for API tools.

User request:
{query}

Conversation context:
{context}

Rules:
- Resolve vague references like "it", "that", "this", "the experiment", or "the theory" using the conversation context.
- Preserve the user's intent, such as videos, podcasts, books, origin, explanation, history, or research papers.
- Return only the rewritten search query.
- Do not answer the user.

Examples:
User request: can you suggest videos that explain where it originated from and what it is
Context topic: Schrodinger's cat
Search query: Schrodinger's cat origin explanation videos
"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You rewrite follow-up requests into precise search queries. Return only the query.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        resolved_query = (response.choices[0].message.content or "").strip()

        if resolved_query:
            return resolved_query[:160]

    except Exception:
        logger.exception("Tool query resolution failed. Using original query.")

    return query


async def choose_follow_up_query(
    original_query: str,
    tool_results: list[ToolResult],
) -> str | None:
    tool_context = format_tool_results(tool_results, max_tokens_per_tool=700)
    
    if not tool_context:
        return None
    
    client = get_openai_client()
    
    prompt = f"""
The user is exploring this topic:
{original_query}

Here are the tool results:
{tool_context}

Pick exactly one connected topic that would be useful to follow next.
The topic should be specific, short, and not identical to the original query.

Return only the topic text.
If there is no useful connected topic, return NONE.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You pick one useful connected research topic. Return only the topic."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        
        topic = (response.choices[0].message.content or "").strip()
        
        if not topic or topic.upper() == "NONE":
            return None
        
        if topic.lower() == original_query.lower():
            return None
        
        return topic[:120]
    
    except Exception:
        logger.exception("Follow-up topic selection failed.")
        return None


async def run_research_tools(query: str, tool_names: list[str]) -> list[ToolResult]:
    results = []
    
    for tool_name in tool_names:
        api_name = TOOL_API_NAMES.get(tool_name, tool_name)
        
        if is_rate_limited(api_name):
            logger.info("Skipping %s: %s is rate-limited", tool_name, api_name)
            continue

        tool = get_tool(tool_name)
        
        for attempt in range(3):
            try:
                result = await tool(query=query)
                mark_api_success(api_name)
                results.append(result)
                break
            
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                
                if status_code == 429:
                    backoff_seconds = calculate_backoff_seconds(
                        api_name=api_name,
                        headers=exc.response.headers,
                    )
                    mark_rate_limited(api_name, cooldown_seconds=backoff_seconds)
                    
                    logger.warning(
                        "Tool %s hit rate limit. Retrying in  %s seconds.",
                        tool_name, 
                        backoff_seconds,
                    )
                
                    if attempt < 2:
                        await asyncio.sleep(backoff_seconds)
                        continue
                    
                logger.warning("Tool %s failed: %s", tool_name, exc)
                break
                
            except Exception as exc:
                logger.exception("Tool %s failed unexpectedly", tool_name)
                break
        
    return results

def format_tool_results(
    tool_results: list[ToolResult],
    max_tokens_per_tool: int = 1500,
) -> str:
    useful_results = [result for result in tool_results if result.sources]

    if not useful_results:
        return ""

    sections = ["External research results:"]

    for result in useful_results:
        tool_sections = [f"\nTool: {result.tool_name}"]

        if result.summary:
            tool_sections.append(f"Summary: {result.summary}")

        for source in result.sources[:5]:
            source_text = f"- [{source.provider} / {source.source_type}] {clean_source_text(source.title)}"

            if source.author:
                source_text += f" by {clean_source_text(source.author)}"

            if source.url:
                source_text += f" ({source.url})"

            if source.summary:
                source_text += f"\n  {clean_source_text(source.summary)}"

            tool_sections.append(source_text)

        tool_text = "\n".join(tool_sections)
        tool_text = truncate_text_to_tokens(
            text=tool_text,
            max_tokens=max_tokens_per_tool,
            model=settings.openai_model,
        )

        sections.append(tool_text)

    return "\n".join(sections)
    
async def run_agent(query: str, context: str | None = None) -> tuple[str, list[ToolResult]]:
    client = get_openai_client()
    
    tool_query = await resolve_tool_query(query=query, context=context)
    tool_names = await choose_tools_with_model(query=query, context=context)
    tool_results = await run_research_tools(query=tool_query, tool_names=tool_names)
    
    follow_up_query = await choose_follow_up_query(
        original_query=query,
        tool_results=tool_results,
    )
    
    if follow_up_query:
        follow_up_tool_names = choose_tools_for_query(follow_up_query)
        
        follow_up_tool_names = [
            tool_name
            for tool_name in follow_up_tool_names
            if tool_name not in {"podcast_search", "youtube_search"}
        ]
        
        follow_up_results = await run_research_tools(
            query=follow_up_query,
            tool_names=follow_up_tool_names[:3],
        )
        
        tool_results.extend(follow_up_results)
        
    tool_context = format_tool_results(tool_results)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    
    if context:
        messages.append(
            {
                "role": "system",
                "content": context,
            }
        )
    
    if tool_context:
        messages.append(
            {
                "role": "system",
                "content": tool_context,
            }
        )
        
    messages.append(
        {
            "role": "user",
            "content": query,
        }
    )
    
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
    )
    
    response_text = response.choices[0].message.content or ""
    return response_text, tool_results
