"""Shared FastAPI dependencies."""

from app.core.database import get_db
from app.core.redis import get_redis

__all__ = ["get_db", "get_redis"]
