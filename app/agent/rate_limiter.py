from datetime import datetime, timedelta, timezone

from app.models.token import RateLimitStatus

DEFAULT_COOLDOWN_SECONDS = 300

_api_cooldowns: dict[str, datetime] = {}

EXTERNAL_APIS = [
    "wikipedia",
    "open_library",
    "arxiv",
    "youtube",
    "podcast_index",
]

def mark_rate_limited(api_name: str, cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS) -> None:
    _api_cooldowns[api_name] = datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)
    
def is_rate_limited(api_name: str) -> bool:
    reset_at = _api_cooldowns.get(api_name)
    
    if reset_at is None:
        return False
    
    if reset_at <= datetime.now(timezone.utc):
        _api_cooldowns.pop(api_name, None)
        return False
    
    return True

def get_rate_limit_status(api_name: str) -> RateLimitStatus:
    reset_at = _api_cooldowns.get(api_name)
    throttled = is_rate_limited(api_name)
    
    return RateLimitStatus(
        api_name=api_name,
        rate_limit_remaining=None,
        rate_limit_reset_at=reset_at if throttled else None,
        is_throttled=throttled,
    )
    
def get_all_rate_limit_statuses() -> list[RateLimitStatus]:
    return [get_rate_limit_status(api_name) for api_name in EXTERNAL_APIS]

def clear_expired_cooldowns() -> None:
    now = datetime.now(timezone.utc)
    
    expired = [
        api_name
        for api_name, reset_at in _api_cooldowns.items()
        if reset_at <= now
    ]
    for api_name in expired:
        _api_cooldowns.pop(api_name, None)