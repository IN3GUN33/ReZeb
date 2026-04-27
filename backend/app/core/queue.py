"""arq queue helpers — enqueue jobs to Redis."""
from __future__ import annotations

from arq.connections import ArqRedis, create_pool, RedisSettings

from app.core.config import get_settings

_pool: ArqRedis | None = None


async def get_queue() -> ArqRedis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_queue_url))
    return _pool


async def enqueue_control_session(session_id: str) -> None:
    queue = await get_queue()
    await queue.enqueue_job("process_control_session", session_id)


async def enqueue_pto_query(query_id: str) -> None:
    queue = await get_queue()
    await queue.enqueue_job("process_pto_query", query_id)
