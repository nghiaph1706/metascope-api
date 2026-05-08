"""Shared Pydantic base schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CustomBaseModel(BaseModel):
    """Base model for all Pydantic schemas."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorResponse(CustomBaseModel):
    """Standard error response format."""

    error: str
    message: str
    details: dict | None = None


class PaginatedResponse(CustomBaseModel, Generic[T]):
    """Cursor-based pagination wrapper."""

    data: list[T]
    next_cursor: str | None = None
    total: int | None = None
