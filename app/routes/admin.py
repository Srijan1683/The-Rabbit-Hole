from fastapi import APIRouter

from app.agent.registry import list_tool_names
from app.models.token import RateLimitStatus

router = APIRouter(tags=["admin"])

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "The Rabbit Hole",
    }
    
@router.get("/tools")
async def list_available_tools():
    return {
        "tools": list_tool_names()
    }
    
@router.get("/rate-limits", response_model=list[RateLimitStatus])
async def get_rate_limits():
    return [
        RateLimitStatus(
            api_name="wikipedia",
            rate_limit_remaining=None,
            rate_limit_reset_at=None,
            is_throttled=False,
        ),
        
        RateLimitStatus(
            api_name="open_library",
            rate_limit_remaining=None,
            rate_limit_reset_at=None,
            is_throttled=False,
        ),
        
        RateLimitStatus(
            api_name="arxiv",
            rate_limit_remaining=None,
            rate_limit_reset_at=None,
            is_throttled=False,
        ),
        
        RateLimitStatus(
            api_name="youtube",
            rate_limit_remaining=None,
            rate_limit_reset_at=None,
            is_throttled=False,
        ),
        
        RateLimitStatus(
            api_name="podcast_index",
            rate_limit_remaining=None,
            rate_limit_reset_at=None,
            is_throttled=False,
        ),
    ]