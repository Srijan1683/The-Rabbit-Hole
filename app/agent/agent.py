from openai import AsyncOpenAI

from app.core.config import settings
from app.agent.prompts import SYSTEM_PROMPT

def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    
async def run_agent(query: str, context: str | None = None) -> str:
    client = get_openai_client()
    
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
    
    return response.choices[0].message.content or ""