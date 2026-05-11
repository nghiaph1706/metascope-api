"""Async Redis client."""

from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import settings

redis_client = Redis.from_url(
    settings.redis_url,
    password=settings.redis_password or None,
    decode_responses=True,
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency — yield Redis client."""
    yield redis_client


async def check_redis_connection() -> None:
    """Verify Redis is reachable."""
    await redis_client.ping()


async def close_redis_client() -> None:
    """Close Redis connection on shutdown."""
    await redis_client.close()
