import random
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from httpx import Headers

from app.models.token import RateLimitStatus

DEFAULT_COOLDOWN_SECONDS = 300
MAX_BACKOFF_SECONDS = 300

_api_cooldowns: dict[str, datetime] = {}
_api_remaining: dict[str, int | None] = {}
_api_reset_time: dict[str, datetime | None] = {}
_api_failures: dict[str, int] = {}

EXTERNAL_APIS = [
    "wikipedia",
    "open_library",
    "arxiv",
    "youtube",
    "podcast_index",
    "openai",
]


def _parse_reset_time(value: str| None) -> datetime | None:
    if not value:
        return None
    
    try:
        reset_seconds = int(value)
        return datetime.now(timezone.utc) + timedelta(seconds=reset_seconds)
    except ValueError:
        pass
    
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None

    
def _parse_retry_after(headers: Headers) -> int | None:
    retry_after = headers.get("retry-after")
    
    if not retry_after:
        return None
    
    try:
        return int(retry_after)
    except ValueError:
        reset_at = _parse_reset_time(retry_after)
        
        if reset_at is None:
            return None
        
        seconds = int((reset_at - datetime.now(timezone.utc)).total_seconds())
        return max(seconds,0)

    
def calculate_backoff_seconds(api_name: str, headers: Headers | None = None) -> int:
    if headers:
        retry_after = _parse_retry_after(headers)
        
        if retry_after is not None:
            return min(retry_after, MAX_BACKOFF_SECONDS)
        
    failures = _api_failures.get(api_name, 0) + 1
    _api_failures[api_name] = failures
    
    exponential_delay = min(2 ** failures, MAX_BACKOFF_SECONDS)
    jitter = random.uniform(0, 1)
    
    return int(exponential_delay + jitter)


def mark_rate_limited(
    api_name: str, 
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
) -> None:
    reset_at = datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)
    _api_cooldowns[api_name] = datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)
    _api_reset_time[api_name] = reset_at
    _api_remaining[api_name] = 0

    
def mark_api_success(api_name: str) -> None:
    _api_failures.pop(api_name, None)
    _api_cooldowns.pop(api_name, None)


def update_rate_limit_from_headers(api_name: str, headers: Headers) -> None:
    remaining_header = (
        headers.get("x-ratelimit-remaining")
        or headers.get("x-rate-limit-remaining")
        or headers.get("ratelimit-remaining")
    )
    
    reset_header = (
        headers.get("x-ratelimit-reset")
        or headers.get("x-rate-limit-reset")
        or headers.get("ratelimit-reset")
    )
    
    if remaining_header is not None:
        try:
            _api_remaining[api_name] = int(remaining_header)
        except ValueError:
            _api_remaining[api_name] = None
    
    reset_at = _parse_reset_time(reset_header)
    
    if reset_at is not None:
        _api_reset_time[api_name] = reset_at

    
def is_rate_limited(api_name: str) -> bool:
    reset_at = _api_cooldowns.get(api_name)
    
    if reset_at is None:
        return False
    
    if reset_at <= datetime.now(timezone.utc):
        _api_cooldowns.pop(api_name, None)
        return False
    
    return True

def get_rate_limit_status(api_name: str) -> RateLimitStatus:
    throttled = is_rate_limited(api_name)
    
    return RateLimitStatus(
        api_name=api_name,
        rate_limit_remaining=_api_remaining.get(api_name),
        rate_limit_reset_at=_api_reset_time.get(api_name) if throttled else None,
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