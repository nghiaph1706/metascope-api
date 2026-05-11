"""Game static data service — query champions, items, traits, augments."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
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
    set_number = set_number or settings.tft_set_number
    cache_key = f"metascope:game:champions:{set_number}:{is_active}:{limit}"

    cached = await cache.cache_get(cache_key)
    if cached is not None:
        return cached

    query = select(Champion)

    if set_number is not None:
        query = query.where(Champion.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Champion.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Champion.is_active == is_active)

    query = query.order_by(Champion.cost.desc(), Champion.name).limit(limit)

    result = await db.execute(query)
    champions = list(result.scalars().all())

    await cache.cache_set(
        cache_key,
        [{"unit_id": c.unit_id, "name": c.name, "cost": c.cost, "traits": c.traits} for c in champions],
        settings.cache_ttl_static_data,
    )
    return champions


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
    set_number = set_number or settings.tft_set_number
    cache_key = f"metascope:game:items:{set_number}:{is_active}:{craftable_only}:{limit}"

    cached = await cache.cache_get(cache_key)
    if cached is not None:
        return cached

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
    items = list(result.scalars().all())

    await cache.cache_set(
        cache_key,
        [{"item_id": i.item_id, "name": i.name, "is_craftable": i.is_craftable, "composition": i.composition} for i in items],
        settings.cache_ttl_static_data,
    )
    return items


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
    set_number = set_number or settings.tft_set_number
    cache_key = f"metascope:game:traits:{set_number}:{is_active}:{limit}"

    cached = await cache.cache_get(cache_key)
    if cached is not None:
        return cached

    query = select(Trait)

    if set_number is not None:
        query = query.where(Trait.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Trait.tft_set_number == settings.tft_set_number)

    if is_active is not None:
        query = query.where(Trait.is_active == is_active)

    query = query.order_by(Trait.name).limit(limit)

    result = await db.execute(query)
    traits = list(result.scalars().all())

    await cache.cache_set(
        cache_key,
        [{"trait_id": t.trait_id, "name": t.name, "breakpoints": t.breakpoints} for t in traits],
        settings.cache_ttl_static_data,
    )
    return traits


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
    set_number = set_number or settings.tft_set_number
    cache_key = f"metascope:game:augments:{set_number}:{is_active}:{tier}:{limit}"

    cached = await cache.cache_get(cache_key)
    if cached is not None:
        return cached

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
    augments = list(result.scalars().all())

    await cache.cache_set(
        cache_key,
        [{"augment_id": a.augment_id, "name": a.name, "tier": a.tier} for a in augments],
        settings.cache_ttl_static_data,
    )
    return augments


async def get_items_cheatsheet(
    db: AsyncSession,
    set_number: int | None = None,
) -> list[Item]:
    """Get craftable items for cheatsheet. Returns items with non-empty composition."""
    from sqlalchemy import func

    set_number = set_number or settings.tft_set_number
    cache_key = f"metascope:game:items_cheatsheet:{set_number}"

    cached = await cache.cache_get(cache_key)
    if cached is not None:
        return cached

    query = select(Item).where(func.cardinality(Item.composition) > 0)

    if set_number is not None:
        query = query.where(Item.tft_set_number == set_number)
    elif settings.tft_set_number:
        query = query.where(Item.tft_set_number == settings.tft_set_number)

    query = query.where(Item.is_active == True).order_by(Item.name)
    result = await db.execute(query)
    items = list(result.scalars().all())

    await cache.cache_set(
        cache_key,
        [{"item_id": i.item_id, "name": i.name, "composition": i.composition} for i in items],
        settings.cache_ttl_static_data,
    )
    return items


async def get_augment_by_id(
    db: AsyncSession,
    augment_id: str,
) -> Augment | None:
    """Get a single augment by augment_id."""
    stmt = select(Augment).where(Augment.augment_id == augment_id)
    result = await db.execute(stmt)
    return result.scalars().first()