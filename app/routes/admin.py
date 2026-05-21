from fastapi import APIRouter

from app.agent.registry import list_tool_names
from app.models.token import RateLimitStatus
from app.agent.rate_limiter import get_all_rate_limit_statuses

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
    return get_all_rate_limit_statuses()