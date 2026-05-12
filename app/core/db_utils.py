"""Shared database utilities."""

from typing import Any

from sqlalchemy import column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

log = get_logger(__name__)


async def upsert_model(
    session: AsyncSession,
    model: Any,
    records: list[dict[str, Any]],
    index_elements: list[str],
    set_columns: dict[str, Any],
) -> None:
    """Bulk upsert records for a given model.

    Args:
        session: Database session.
        model: SQLAlchemy model class (Champion, Item, Augment, Trait).
        records: List of dicts to insert/update.
        index_elements: Primary key column names for conflict detection.
        set_columns: Columns to update on conflict. Supports SQLAlchemy column
            expressions (e.g. column("excluded.name")) or plain strings
            (e.g. "name" -> auto-resolved to excluded.name).
    """
    if not records:
        return

    resolved_columns: dict[str, Any] = {}
    for col_name, col_value in set_columns.items():
        if isinstance(col_value, str):
            if col_value.startswith("excluded."):
                resolved_columns[col_name] = column(col_value)
            else:
                resolved_columns[col_name] = column(f"excluded.{col_value}")
        else:
            resolved_columns[col_name] = col_value

    stmt = pg_insert(model).values(records)
    stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=resolved_columns)
    await session.execute(stmt)
    log.info("upserted_records", model=model.__name__, count=len(records))
