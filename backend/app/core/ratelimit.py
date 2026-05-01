"""Redis sliding window rate limiter."""

from __future__ import annotations

import time
from uuid import UUID

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.exceptions import LimitExceededError

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(user_id: UUID | str, action: str = "api") -> None:
    """Sliding window: {rate_limit_per_user} requests per {rate_limit_window_seconds}."""
    settings = get_settings()
    r = get_redis()
    key = f"rl:{user_id}:{action}"
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, settings.rate_limit_window_seconds)
    results = await pipe.execute()

    count = results[2]
    if count > settings.rate_limit_per_user:
        raise LimitExceededError(
            f"Rate limit exceeded: {settings.rate_limit_per_user} requests per "
            f"{settings.rate_limit_window_seconds}s"
        )
