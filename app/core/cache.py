"""Generic Redis cache helpers."""

import json
from typing import Any

from app.core import redis
from app.core.logging import get_logger

log = get_logger(__name__)
CACHE_KEY_PREFIX = "metascope"


async def cache_get(key: str) -> Any | None:
    """Get a value from Redis cache. Returns None on miss or error."""
    try:
        data = await redis.redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception as exc:
        log.warning("cache_get_error", key=key, error=str(exc))
    return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """Set a value in Redis cache with TTL. Silently ignores errors."""
    try:
        await redis.redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        log.warning("cache_set_error", key=key, error=str(exc))


async def cache_delete(key: str) -> None:
    """Delete a key from Redis cache. Silently ignores errors."""
    try:
        await redis.redis_client.delete(key)
    except Exception as exc:
        log.warning("cache_delete_error", key=key, error=str(exc))


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern. Silently ignores errors."""
    try:
        cursor = 0
        while True:
            cursor, keys = await redis.redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        log.warning("cache_delete_pattern_error", pattern=pattern, error=str(exc))


async def cache_get_or_set(key: str, ttl: int, fetch_fn, *args, **kwargs) -> Any:
    """Get from cache or fetch and cache. Returns (value, cache_hit)."""
    cached = await cache_get(key)
    if cached is not None:
        return cached, True

    value = await fetch_fn(*args, **kwargs)
    if value is not None:
        await cache_set(key, value, ttl)
    return value, False