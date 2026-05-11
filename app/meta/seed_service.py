"""Seed static data from DataDragon CDN into PostgreSQL."""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.meta.models import Augment, Champion, Item, Trait
from app.ports.data_dragon.client import DataDragonClient
from app.ports.data_dragon.transformer import (
    determine_set_number,
    transform_augment,
    transform_champion,
    transform_item,
    transform_trait,
)

log = get_logger(__name__)


async def _upsert_model(
    session: AsyncSession,
    model: type[Champion] | type[Item] | type[Augment] | type[Trait],
    records: list[dict[str, Any]],
    index_elements: list[str],
    set_columns: dict[str, Any],
) -> None:
    """Bulk upsert records for a given model."""
    if not records:
        return
    stmt = pg_insert(model).values(records)
    stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=set_columns)
    await session.execute(stmt)
    log.info("upserted_records", model=model.__name__, count=len(records))


async def seed_all(client: DataDragonClient, session: AsyncSession) -> dict[str, int]:
    """Fetch DataDragon data and upsert all four model types.

    Returns a summary dict with counts of each model type seeded.
    """
    version = await client.get_latest_version()
    log.info("datadragon_seed_start", version=version)

    patch_major = int(version.split(".")[0]) if version else None
    set_data = await client.get_set_data(version)
    set_number = determine_set_number(set_data, patch_major)
    patch = version

    # ── Champions ─────────────────────────────────────────────────
    champ_data = (await client.get_champions(version)).get("data", {})
    champion_records = [
        transform_champion(v, set_number, patch) for v in champ_data.values()
    ]
    await _upsert_model(
        session,
        Champion,
        champion_records,
        index_elements=["unit_id"],
        set_columns={
            "name": pg_insert(Champion).excluded.name,
            "cost": pg_insert(Champion).excluded.cost,
            "traits": pg_insert(Champion).excluded.traits,
            "ability_name": pg_insert(Champion).excluded.ability_name,
            "ability_desc": pg_insert(Champion).excluded.ability_desc,
            "stats": pg_insert(Champion).excluded.stats,
            "tft_set_number": pg_insert(Champion).excluded.tft_set_number,
            "patch_added": pg_insert(Champion).excluded.patch_added,
            "is_active": pg_insert(Champion).excluded.is_active,
        },
    )

    # ── Items ────────────────────────────────────────────────────
    item_data = (await client.get_items(version)).get("data", {})
    item_records = [transform_item(v, set_number) for v in item_data.values()]
    await _upsert_model(
        session,
        Item,
        item_records,
        index_elements=["item_id"],
        set_columns={
            "name": pg_insert(Item).excluded.name,
            "description": pg_insert(Item).excluded.description,
            "icon": pg_insert(Item).excluded.icon,
            "is_component": pg_insert(Item).excluded.is_component,
            "is_craftable": pg_insert(Item).excluded.is_craftable,
            "is_embleme": pg_insert(Item).excluded.is_embleme,
            "is_spatula": pg_insert(Item).excluded.is_spatula,
            "composition": pg_insert(Item).excluded.composition,
            "stats": pg_insert(Item).excluded.stats,
            "tft_set_number": pg_insert(Item).excluded.tft_set_number,
            "is_active": pg_insert(Item).excluded.is_active,
        },
    )

    # ── Augments ──────────────────────────────────────────────────
    aug_data = (await client.get_augments(version)).get("data", {})
    aug_records = [transform_augment(v, set_number) for v in aug_data.values()]
    await _upsert_model(
        session,
        Augment,
        aug_records,
        index_elements=["augment_id"],
        set_columns={
            "name": pg_insert(Augment).excluded.name,
            "description": pg_insert(Augment).excluded.description,
            "tier": pg_insert(Augment).excluded.tier,
            "icon": pg_insert(Augment).excluded.icon,
            "tft_set_number": pg_insert(Augment).excluded.tft_set_number,
            "is_active": pg_insert(Augment).excluded.is_active,
        },
    )

    # ── Traits ────────────────────────────────────────────────────
    trait_data = (await client.get_traits(version)).get("data", {})
    trait_records = [transform_trait(v, set_number) for v in trait_data.values()]
    await _upsert_model(
        session,
        Trait,
        trait_records,
        index_elements=["trait_id"],
        set_columns={
            "name": pg_insert(Trait).excluded.name,
            "description": pg_insert(Trait).excluded.description,
            "tft_set_number": pg_insert(Trait).excluded.tft_set_number,
            "breakpoints": pg_insert(Trait).excluded.breakpoints,
            "is_active": pg_insert(Trait).excluded.is_active,
        },
    )

    await session.commit()
    log.info(
        "datadragon_seed_complete",
        version=version,
        set_number=set_number,
        champions=len(champion_records),
        items=len(item_records),
        augments=len(aug_records),
        traits=len(trait_records),
    )
    return {
        "champions": len(champion_records),
        "items": len(item_records),
        "augments": len(aug_records),
        "traits": len(trait_records),
    }
