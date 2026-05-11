"""Meta & Analytics API routes — stats, tier list, patches."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.meta.models import Augment, AugmentStats, Champion, ChampionStats, Item, ItemStats

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.config import settings
from app.core.dependencies import get_db
from app.core.exceptions import InsufficientDataError
from app.match.models import Match
from app.meta import stats_service
from app.meta.models import Augment, AugmentStats, Champion, ChampionStats, Item, ItemStats
from app.meta.schemas import (
    AugmentStatsResponse,
    ChampionStatsDetailResponse,
    ChampionStatsResponse,
    ItemStatsResponse,
    PatchListResponse,
    TierListResponse,
)

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/tier-list", response_model=TierListResponse)
async def get_tier_list(
    response: Response,
    patch: str | None = Query(default=None),
    tft_set_number: int | None = Query(default=None),
    queue_type: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> TierListResponse:
    """Get champion tier list ranked by tier score.

    Tier score = win_rate*0.35 + (1-avg_placement/8)*0.35*100 + pick_rate*0.30
    """
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number
    if patch is None:
        patch = await _get_latest_patch(db)

    cache_key = f"metascope:meta:tier_list:{patch}:{tft_set_number}:{queue_type}"
    cached = await cache.cache_get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return TierListResponse(**cached)

    response.headers["X-Cache"] = "MISS"

    # Check if stats exist for this patch
    stats_exist = await _stats_exist(db, ChampionStats, patch, tft_set_number)
    if not stats_exist:
        raise InsufficientDataError(
            f"No stats data for patch {patch}. Run stats calculation first.",
            details={"patch": patch},
        )

    # Query champion stats with champion info
    stmt = (
        select(ChampionStats, Champion)
        .join(Champion, ChampionStats.champion_id == Champion.unit_id)
        .where(
            ChampionStats.patch == patch,
            ChampionStats.tft_set_number == tft_set_number,
            ChampionStats.queue_type == queue_type,
        )
        .order_by(ChampionStats.tier_score.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    data = []
    for stats, champ in rows:
        data.append(
            ChampionStatsResponse(
                champion_id=stats.champion_id,
                name=champ.name if champ else None,
                cost=champ.cost if champ else None,
                traits=champ.traits if champ else [],
                games_played=stats.games_played,
                wins=stats.wins,
                top4s=stats.top4s,
                win_rate=_to_float(stats.win_rate),
                top4_rate=_to_float(stats.top4_rate),
                avg_placement=_to_float(stats.avg_placement),
                pick_rate=_to_float(stats.pick_rate),
                tier_score=_to_float(stats.tier_score),
                tier=stats.tier or "D",
                patch=stats.patch,
                tft_set_number=stats.tft_set_number,
            )
        )

    resp = TierListResponse(
        data=data,
        total=len(data),
        patch=patch,
        tft_set_number=tft_set_number,
    )

    await cache.cache_set(
        cache_key,
        resp.model_dump(mode="json"),
        settings.cache_ttl_tier_list,
    )
    return resp


@router.get("/champions/{champion_id}/stats", response_model=ChampionStatsDetailResponse)
async def get_champion_stats(
    champion_id: str,
    patch: str | None = Query(default=None),
    tft_set_number: int | None = Query(default=None),
    queue_type: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> ChampionStatsDetailResponse:
    """Get detailed stats for a specific champion."""
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number
    if patch is None:
        patch = await _get_latest_patch(db)

    # Get champion info
    champ_stmt = select(Champion).where(Champion.unit_id == champion_id)
    champ_result = await db.execute(champ_stmt)
    champ = champ_result.scalars().first()

    # Get stats
    stats_stmt = (
        select(ChampionStats)
        .where(
            ChampionStats.champion_id == champion_id,
            ChampionStats.patch == patch,
            ChampionStats.tft_set_number == tft_set_number,
            ChampionStats.queue_type == queue_type,
        )
        .order_by(ChampionStats.calculated_at.desc())
        .limit(1)
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.scalars().first()

    if not stats:
        raise InsufficientDataError(
            f"No stats for champion {champion_id} on patch {patch}",
            details={"champion_id": champion_id, "patch": patch},
        )

    return ChampionStatsDetailResponse(
        champion_id=stats.champion_id,
        name=champ.name if champ else None,
        cost=champ.cost if champ else None,
        traits=champ.traits if champ else [],
        games_played=stats.games_played,
        wins=stats.wins,
        top4s=stats.top4s,
        win_rate=_to_float(stats.win_rate),
        top4_rate=_to_float(stats.top4_rate),
        avg_placement=_to_float(stats.avg_placement),
        pick_rate=_to_float(stats.pick_rate),
        tier_score=_to_float(stats.tier_score),
        tier=stats.tier or "D",
        patch=stats.patch,
        tft_set_number=stats.tft_set_number,
        stats=champ.stats if champ else {},
        ability_name=champ.ability_name if champ else None,
        ability_desc=champ.ability_desc if champ else None,
    )


@router.get("/items/{item_id}/stats", response_model=ItemStatsResponse)
async def get_item_stats(
    item_id: str,
    patch: str | None = Query(default=None),
    tft_set_number: int | None = Query(default=None),
    queue_type: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> ItemStatsResponse:
    """Get detailed stats for a specific item."""
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number
    if patch is None:
        patch = await _get_latest_patch(db)

    # Get item info
    item_stmt = select(Item).where(Item.item_id == item_id)
    item_result = await db.execute(item_stmt)
    item = item_result.scalars().first()

    # Get stats (overall only for now)
    stats_stmt = (
        select(ItemStats)
        .where(
            ItemStats.item_id == item_id,
            ItemStats.champion_id == "_overall",
            ItemStats.patch == patch,
            ItemStats.tft_set_number == tft_set_number,
            ItemStats.queue_type == queue_type,
        )
        .order_by(ItemStats.calculated_at.desc())
        .limit(1)
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.scalars().first()

    if not stats:
        raise InsufficientDataError(
            f"No stats for item {item_id} on patch {patch}",
            details={"item_id": item_id, "patch": patch},
        )

    return ItemStatsResponse(
        item_id=stats.item_id,
        name=item.name if item else None,
        games_played=stats.games_played,
        win_rate=_to_float(stats.win_rate),
        top4_rate=_to_float(stats.top4_rate),
        avg_placement=_to_float(stats.avg_placement),
        is_craftable=item.is_craftable if item else False,
        composition=item.composition if item else [],
        stats=item.stats if item else {},
        tier=None,
        patch=stats.patch,
        tft_set_number=stats.tft_set_number,
    )


@router.get("/augments/{augment_id}/stats", response_model=AugmentStatsResponse)
async def get_augment_stats(
    augment_id: str,
    patch: str | None = Query(default=None),
    tft_set_number: int | None = Query(default=None),
    queue_type: str = Query(default="ranked"),
    db: AsyncSession = Depends(get_db),
) -> AugmentStatsResponse:
    """Get detailed stats for a specific augment."""
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number
    if patch is None:
        patch = await _get_latest_patch(db)

    # Get augment info
    aug_stmt = select(Augment).where(Augment.augment_id == augment_id)
    aug_result = await db.execute(aug_stmt)
    aug = aug_result.scalars().first()

    # Get stats
    stats_stmt = (
        select(AugmentStats)
        .where(
            AugmentStats.augment_id == augment_id,
            AugmentStats.patch == patch,
            AugmentStats.tft_set_number == tft_set_number,
            AugmentStats.queue_type == queue_type,
            AugmentStats.stage == "_all",
        )
        .order_by(AugmentStats.calculated_at.desc())
        .limit(1)
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.scalars().first()

    if not stats:
        raise InsufficientDataError(
            f"No stats for augment {augment_id} on patch {patch}",
            details={"augment_id": augment_id, "patch": patch},
        )

    return AugmentStatsResponse(
        augment_id=stats.augment_id,
        name=aug.name if aug else None,
        tier=aug.tier if aug else 1,
        description=aug.description if aug else None,
        games_played=stats.games_played,
        win_rate=_to_float(stats.win_rate),
        top4_rate=_to_float(stats.top4_rate),
        avg_placement=_to_float(stats.avg_placement),
        patch=stats.patch,
        tft_set_number=stats.tft_set_number,
    )


@router.get("/patches", response_model=PatchListResponse)
async def get_patches(
    db: AsyncSession = Depends(get_db),
) -> PatchListResponse:
    """Get list of patches with match data."""
    stmt = (
        select(Match.patch, func.count(Match.id))
        .group_by(Match.patch)
        .order_by(Match.game_datetime.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    patches = [row[0] for row in rows if row[0]]
    return PatchListResponse(data=patches, total=len(patches))


@router.post("/calculate-stats")
async def calculate_stats(
    patch: str | None = Query(default=None),
    tft_set_number: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Calculate all stats for a patch (admin endpoint).

    This is a compute-intensive operation that aggregates match data.
    Should be called via Celery task, not directly by users.
    """
    result = await stats_service.calculate_all_stats(db, patch, tft_set_number)
    # Invalidate meta cache after recalculation
    await cache.cache_delete_pattern("metascope:meta:*")
    return result


async def _get_latest_patch(db: AsyncSession) -> str:
    """Get the most recent patch from match data."""
    stmt = select(Match.patch).order_by(Match.game_datetime.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar() or str(settings.tft_set_number)


async def _stats_exist(
    db: AsyncSession,
    model: type[ChampionStats],
    patch: str,
    tft_set_number: int,
) -> bool:
    """Check if stats exist for a given patch and set."""
    stmt = (
        select(func.count())
        .select_from(model)
        .where(model.patch == patch, model.tft_set_number == tft_set_number)
        .limit(1)
    )
    result = await db.execute(stmt)
    count = result.scalar()
    return count is not None and count > 0


def _to_float(value: Any) -> float:
    """Convert Decimal or None to float."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)  # cast non-Decimal numerics
