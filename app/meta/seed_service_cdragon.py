"""Seed complete static data from Community Dragon CDN.

Unlike DataDragon CDN which only has minimal data (name, icon),
Community Dragon provides full champion stats, abilities, trait breakpoints,
and item compositions.
"""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.meta.models import Augment, Champion, Item, Trait
from app.ports.community_dragon.client import CommunityDragonClient
from app.ports.community_dragon.transformer import (
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


async def seed_from_community_dragon(
    client: CommunityDragonClient, session: AsyncSession, use_pbe: bool = False
) -> dict[str, int]:
    """Fetch complete TFT data from Community Dragon and upsert all model types.

    Community Dragon has ALL data in one endpoint: champions with stats/abilities,
    item compositions, trait breakpoints, augments - for ALL sets in one request.
    """
    data = await client.get_tft_data(use_pbe)
    version = "latest" if use_pbe else "live"

    # Build lookup dicts from root items array (both items AND augments are here)
    all_items_by_api: dict[str, dict[str, Any]] = {}
    for item in data.get("items", []):
        api_name = item.get("apiName")
        if api_name:
            all_items_by_api[api_name] = item

    sets_meta = data.get("sets", {})
    set_data_arr = data.get("setData", [])

    total_champs = total_items = total_augs = total_traits = 0

    for set_info in set_data_arr:
        set_number = set_info.get("number")
        set_name = set_info.get("name", "")

        if not set_number:
            continue

        log.info("seeding_set", set_number=set_number, set_name=set_name)

        # ── Champions ─────────────────────────────────────────────
        # Deduplicate by unit_id - keep latest set version
        champ_records = []
        seen_unit_ids: set[str] = set()
        for raw_champ in set_info.get("champions", []):
            record = transform_champion(raw_champ, set_number, version)
            if record and record["unit_id"] not in seen_unit_ids:
                champ_records.append(record)
                seen_unit_ids.add(record["unit_id"])
        if champ_records:
            await _upsert_model(
                session,
                Champion,
                champ_records,
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
        total_champs += len(champ_records)

        # ── Traits ─────────────────────────────────────────────────
        # Deduplicate by trait_id
        trait_records = []
        seen_trait_ids: set[str] = set()
        for raw_trait in set_info.get("traits", []):
            trait_id = raw_trait.get("apiName", "")
            if trait_id and trait_id not in seen_trait_ids:
                trait_records.append(transform_trait(raw_trait, set_number))
                seen_trait_ids.add(trait_id)
        if trait_records:
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
        total_traits += len(trait_records)

        # ── Augments ──────────────────────────────────────────────
        # Augments in setInfo are just apiName strings, look up full data
        # Deduplicate by augment_id
        aug_records = []
        seen_aug_ids: set[str] = set()
        for aug_api_name in set_info.get("augments", []):
            if aug_api_name in all_items_by_api and aug_api_name not in seen_aug_ids:
                raw_aug = all_items_by_api[aug_api_name]
                aug_records.append(transform_augment(raw_aug, set_number))
                seen_aug_ids.add(aug_api_name)
        if aug_records:
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
        total_augs += len(aug_records)

        # ── Items ─────────────────────────────────────────────────
        # Items in setInfo are just apiName strings, look up full data
        # Deduplicate by item_id
        item_records = []
        seen_item_ids: set[str] = set()
        for item_api_name in set_info.get("items", []):
            if item_api_name in all_items_by_api and item_api_name not in seen_item_ids:
                raw_item = all_items_by_api[item_api_name]
                record = transform_item(raw_item, set_number)
                if record:
                    item_records.append(record)
                    seen_item_ids.add(item_api_name)
        if item_records:
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
        total_items += len(item_records)

    await session.commit()
    log.info(
        "community_dragon_seed_complete",
        version=version,
        champions=total_champs,
        items=total_items,
        augments=total_augs,
        traits=total_traits,
    )
    return {
        "champions": total_champs,
        "items": total_items,
        "augments": total_augs,
        "traits": total_traits,
    }
