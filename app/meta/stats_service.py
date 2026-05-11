"""Stats calculation service — compute champion/item/augment/trait stats from match data."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.match.models import Match, MatchParticipant, ParticipantUnit
from app.meta.models import AugmentStats, ChampionStats, ItemStats

log = get_logger(__name__)

QUEUE_TYPE = "ranked"


async def calculate_champion_stats(
    db: AsyncSession,
    patch: str | None = None,
    tft_set_number: int | None = None,
    queue_type: str = QUEUE_TYPE,
) -> dict[str, Any]:
    """Calculate champion stats from match data.

    Aggregates match participants to compute:
    - games_played: total matches using this champion
    - wins: placement == 1
    - top4s: placement <= 4
    - total_placement: sum of all placements
    - win_rate, top4_rate, avg_placement, pick_rate
    - tier_score: win_rate*0.35 + (1-avg_placement/8)*0.35 + pick_rate*0.30
    - tier: S/A/B/C/D based on tier_score thresholds
    """
    if patch is None:
        patch = await _get_latest_patch(db)
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number

    # Query: join matches + participants + units to get champion usage
    stmt = (
        select(
            ParticipantUnit.unit_id,
            func.count(Match.id).label("games"),
            func.sum(MatchParticipant.placement == 1).label("wins"),
            func.sum(MatchParticipant.placement <= 4).label("top4s"),
            func.sum(MatchParticipant.placement).label("total_placement"),
        )
        .join(MatchParticipant, ParticipantUnit.participant_id == MatchParticipant.id)
        .join(Match, MatchParticipant.match_id == Match.id)
        .where(
            Match.patch == patch,
            MatchParticipant.placement.isnot(None),
        )
        .group_by(ParticipantUnit.unit_id)
    )

    result = await db.execute(stmt)
    rows = result.all()

    total_games = await _get_total_games(db, patch, queue_type)
    tier_boundaries = settings.tier_boundaries_map

    stats_records: list[ChampionStats] = []
    for row in rows:
        unit_id = row.unit_id
        games = row.games or 0
        wins = int(row.wins or 0)
        top4s = int(row.top4s or 0)
        total_placement = row.total_placement or 0

        if games == 0:
            continue

        win_rate = Decimal(wins) / Decimal(games) * 100
        top4_rate = Decimal(top4s) / Decimal(games) * 100
        avg_placement = Decimal(total_placement) / Decimal(games)
        pick_rate = Decimal(games) / Decimal(total_games) * 100 if total_games > 0 else Decimal(0)

        # Tier score formula from FEATURES.md
        tier_score = (
            float(win_rate) * 0.35
            + float(1 - float(avg_placement) / 8) * 0.35 * 100
            + float(pick_rate) * 0.30
        )

        tier = _score_to_tier(tier_score, tier_boundaries)

        stats_records.append(
            ChampionStats(
                champion_id=unit_id,
                tft_set_number=tft_set_number,
                patch=patch,
                queue_type=queue_type,
                calculated_at=datetime.utcnow(),
                games_played=games,
                wins=wins,
                top4s=top4s,
                total_placement=total_placement,
                win_rate=win_rate,
                top4_rate=top4_rate,
                avg_placement=avg_placement,
                pick_rate=pick_rate,
                tier_score=Decimal(tier_score),
                tier=tier,
            )
        )

    # Bulk upsert
    for stats in stats_records:
        db.add(stats)

    await db.flush()
    log.info("champion_stats_calculated", patch=patch, count=len(stats_records))
    return {"patch": patch, "champions": len(stats_records)}


async def calculate_item_stats(
    db: AsyncSession,
    patch: str | None = None,
    tft_set_number: int | None = None,
    queue_type: str = QUEUE_TYPE,
) -> dict[str, Any]:
    """Calculate item stats from match data."""
    if patch is None:
        patch = await _get_latest_patch(db)
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number

    # Items are in participant_units.items (list of item_ids)
    # Need to explode the items array - SQLAlchemy doesn't support array unnesting well in async
    # For now, query and process in Python
    stmt = (
        select(MatchParticipant, ParticipantUnit)
        .join(Match, MatchParticipant.match_id == Match.id)
        .join(ParticipantUnit, ParticipantUnit.participant_id == MatchParticipant.id)
        .where(Match.patch == patch)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Aggregate item stats in memory
    item_agg: dict[str, dict[str, Any]] = {}
    for participant, unit in rows:
        placement = participant.placement
        if placement is None:
            continue
        is_win = placement == 1
        is_top4 = placement <= 4

        for item_id in unit.items or []:
            if item_id not in item_agg:
                item_agg[item_id] = {"games": 0, "wins": 0, "top4s": 0, "placements": 0}
            item_agg[item_id]["games"] += 1
            item_agg[item_id]["wins"] += int(is_win)
            item_agg[item_id]["top4s"] += int(is_top4)
            item_agg[item_id]["placements"] += placement

    stats_records = []

    for item_id, agg in item_agg.items():
        games = agg["games"]
        if games == 0:
            continue

        win_rate = Decimal(agg["wins"]) / Decimal(games) * 100
        top4_rate = Decimal(agg["top4s"]) / Decimal(games) * 100
        avg_placement = Decimal(agg["placements"]) / Decimal(games)

        stats_records.append(
            ItemStats(
                item_id=item_id,
                champion_id="_overall",
                tft_set_number=tft_set_number,
                patch=patch,
                queue_type=queue_type,
                calculated_at=datetime.utcnow(),
                games_played=games,
                win_rate=win_rate,
                top4_rate=top4_rate,
                avg_placement=avg_placement,
            )
        )

    for stats in stats_records:
        db.add(stats)

    await db.flush()
    log.info("item_stats_calculated", patch=patch, count=len(stats_records))
    return {"patch": patch, "items": len(stats_records)}


async def calculate_augment_stats(
    db: AsyncSession,
    patch: str | None = None,
    tft_set_number: int | None = None,
    queue_type: str = QUEUE_TYPE,
) -> dict[str, Any]:
    """Calculate augment stats from match data."""
    if patch is None:
        patch = await _get_latest_patch(db)
    if tft_set_number is None:
        tft_set_number = settings.tft_set_number

    stmt = (
        select(MatchParticipant, Match)
        .join(Match, MatchParticipant.match_id == Match.id)
        .where(Match.patch == patch)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Aggregate augment stats in memory
    aug_agg: dict[str, dict[str, Any]] = {}
    for participant, _match in rows:
        placement = participant.placement
        if placement is None:
            continue
        is_win = placement == 1
        is_top4 = placement <= 4

        for aug_id in participant.augments or []:
            if aug_id not in aug_agg:
                aug_agg[aug_id] = {"games": 0, "wins": 0, "top4s": 0, "placements": 0}
            aug_agg[aug_id]["games"] += 1
            aug_agg[aug_id]["wins"] += int(is_win)
            aug_agg[aug_id]["top4s"] += int(is_top4)
            aug_agg[aug_id]["placements"] += placement

    stats_records = []

    for aug_id, agg in aug_agg.items():
        games = agg["games"]
        if games == 0:
            continue

        win_rate = Decimal(agg["wins"]) / Decimal(games) * 100
        top4_rate = Decimal(agg["top4s"]) / Decimal(games) * 100
        avg_placement = Decimal(agg["placements"]) / Decimal(games)

        stats_records.append(
            AugmentStats(
                augment_id=aug_id,
                tft_set_number=tft_set_number,
                patch=patch,
                queue_type=queue_type,
                stage="_all",
                calculated_at=datetime.utcnow(),
                games_played=games,
                win_rate=win_rate,
                top4_rate=top4_rate,
                avg_placement=avg_placement,
            )
        )

    for stats in stats_records:
        db.add(stats)

    await db.flush()
    log.info("augment_stats_calculated", patch=patch, count=len(stats_records))
    return {"patch": patch, "augments": len(stats_records)}


async def calculate_all_stats(
    db: AsyncSession,
    patch: str | None = None,
    tft_set_number: int | None = None,
) -> dict[str, Any]:
    """Calculate all stats (champions, items, augments) for a patch."""
    result = {}
    result["champions"] = await calculate_champion_stats(db, patch, tft_set_number)
    result["items"] = await calculate_item_stats(db, patch, tft_set_number)
    result["augments"] = await calculate_augment_stats(db, patch, tft_set_number)
    await db.commit()
    return result


async def _get_latest_patch(db: AsyncSession) -> str:
    """Get the most recent patch from match data."""
    stmt = select(Match.patch).order_by(Match.game_datetime.desc()).limit(1)
    result = await db.execute(stmt)
    patch = result.scalar()
    return patch or str(settings.tft_set_number)


async def _get_total_games(db: AsyncSession, patch: str, queue_type: str) -> int:
    """Get total games played in a patch for pick_rate calculation."""
    stmt = select(func.count(Match.id)).where(Match.patch == patch)
    result = await db.execute(stmt)
    return result.scalar() or 1


def _score_to_tier(score: float, boundaries: dict[str, int]) -> str:
    """Convert tier score to tier letter (S/A/B/C/D)."""
    if score >= boundaries.get("S", 90):
        return "S"
    elif score >= boundaries.get("A", 70):
        return "A"
    elif score >= boundaries.get("B", 45):
        return "B"
    elif score >= boundaries.get("C", 20):
        return "C"
    else:
        return "D"
