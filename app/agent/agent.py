import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.rate_limiter import is_rate_limited, mark_rate_limited
from app.agent.registry import get_tool
from app.models.tool import ToolResult
from app.core.logging import get_logger

TOOL_API_NAMES = {
    "wikipedia_summary": "wikipedia",
    "wikipedia_search": "wikipedia",
    "open_library_search": "open_library",
    "arxiv_search": "arxiv",
    "youtube_search": "youtube",
    "podcast_search": "podcast_index",
}

logger = get_logger(__name__)

def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

def choose_tools_for_query(query: str) -> list[str]:
    query_lower = query.lower()
    tools = ["wikipedia_summary"]
    
    if any(word in query_lower for word in ["book", "read", "author", "novel", "biography"]):
        tools.append("open_library_search")
        
    if any(word in query_lower for word in ["research", "paper", "study", "science", "technical", "physics", "math", "ai", "quantum"]):
        tools.append("arxiv_search")
        
    if any(word in query_lower for word in ["video", "watch", "youtube", "lecture", "documentary", "talk"]):
        tools.append("youtube_search")
        
    if any(word in query_lower for word in ["podcast", "listen", "audio", "episode"]):
        tools.append("podcast_search")
        
    return tools

async def run_research_tools(query: str, tool_names: list[str]) -> list[ToolResult]:
    results = []
    
    for tool_name in tool_names:
        api_name = TOOL_API_NAMES.get(tool_name, tool_name)
        if is_rate_limited(api_name):
            logger.info("Skipping %s: %s is rate-limited", tool_name, api_name)
            continue

        tool = get_tool(tool_name)
        try:
            result = await tool(query=query)
            results.append(result)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                mark_rate_limited(api_name)
            logger.warning("Tool %s failed: %s", tool_name, exc)
        except Exception as exc:
            logger.exception("Tool %s failed unexpectedly", tool_name)
        
    return results

def format_tool_results(tool_results: list[ToolResult]) -> str:
    useful_results = [result for result in tool_results if result.sources]
    
    if not useful_results:
        return ""
    
    sections = ["External research results:"]
    
    for result in useful_results:
        sections.append(f"\nTool: {result.tool_name}")
        
        if result.summary:
            sections.append(f"Summary: {result.summary}")
            
        for source in result.sources[:5]:
            source_text = f"- {source.title}"
            
            if source.author:
                source_text += f" by {source.author}"
                
            if source.url:
                source_text += f" ({source.url})"
                
            if source.summary:
                source_text += f"\n {source.summary}"
                
            sections.append(source_text)
            
    return "\n".join(sections)
    
async def run_agent(query: str, context: str | None = None) -> tuple[str, list[ToolResult]]:
    client = get_openai_client()
    
    tool_names = choose_tools_for_query(query)
    tool_results = await run_research_tools(query=query, tool_names=tool_names)
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
