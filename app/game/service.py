"""Game static data service — query champions, items, traits, augments."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.meta.models import Augment, Champion, Item, Trait

log = get_logger(__name__)


async def get_champions(
    db: AsyncSession,
    set_number: int | None = None,
    is_active: bool = True,
    limit: int = 100,
) -> list[Champion]:
    """Get champion list with optional set filter."""
    query = select(Champion)

    if set_number is not None:
        query = query.where(Champion.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Champion.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Champion.is_active == is_active)

    query = query.order_by(Champion.cost.desc(), Champion.name).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_champion_by_id(
    db: AsyncSession,
    unit_id: str,
) -> Champion | None:
    """Get a single champion by unit_id."""
    stmt = select(Champion).where(Champion.unit_id == unit_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_items(
    db: AsyncSession,
    set_number: int | None = None,
    is_active: bool = True,
    craftable_only: bool = False,
    limit: int = 200,
) -> list[Item]:
    """Get item list with optional filters."""
    query = select(Item)

    if set_number is not None:
        query = query.where(Item.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Item.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Item.is_active == is_active)

    if craftable_only:
        query = query.where(Item.is_craftable == True)

    query = query.order_by(Item.name).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_item_by_id(
    db: AsyncSession,
    item_id: str,
) -> Item | None:
    """Get a single item by item_id."""
    stmt = select(Item).where(Item.item_id == item_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_traits(
    db: AsyncSession,
    set_number: int | None = None,
    is_active: bool = True,
    limit: int = 100,
) -> list[Trait]:
    """Get trait list with optional set filter."""
    query = select(Trait)

    if set_number is not None:
        query = query.where(Trait.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Trait.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Trait.is_active == is_active)

    query = query.order_by(Trait.name).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_trait_by_id(
    db: AsyncSession,
    trait_id: str,
) -> Trait | None:
    """Get a single trait by trait_id."""
    stmt = select(Trait).where(Trait.trait_id == trait_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_augments(
    db: AsyncSession,
    set_number: int | None = None,
    is_active: bool = True,
    tier: int | None = None,
    limit: int = 200,
) -> list[Augment]:
    """Get augment list with optional filters."""
    query = select(Augment)

    if set_number is not None:
        query = query.where(Augment.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Augment.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Augment.is_active == is_active)

    if tier is not None:
        query = query.where(Augment.tier == tier)

    query = query.order_by(Augment.tier, Augment.name).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_items_cheatsheet(
    db: AsyncSession,
    set_number: int | None = None,
) -> list[Item]:
    """Get craftable items for cheatsheet. Returns items with non-empty composition."""
    from sqlalchemy import func
    query = select(Item).where(func.cardinality(Item.composition) > 0)

    if set_number is not None:
        query = query.where(Item.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Item.tft_set_number == settings.tft_set_number)

    query = query.where(Item.is_active == True).order_by(Item.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_augment_by_id(
    db: AsyncSession,
    augment_id: str,
) -> Augment | None:
    """Get a single augment by augment_id."""
    stmt = select(Augment).where(Augment.augment_id == augment_id)
    result = await db.execute(stmt)
    return result.scalars().first()