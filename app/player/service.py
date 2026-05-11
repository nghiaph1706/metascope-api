"""Player business logic."""

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import cache
from app.core.config import settings
from app.match.models import Match, MatchParticipant, ParticipantUnit
from app.meta.models import Augment, Champion
from app.player.exceptions import PlayerNotFoundError
from app.player.models import Player
from app.player.schemas import AugmentUseStat, ChampionUseStat, PlayerStatsResponse
from app.ports.riot.client import RiotClient
from app.ports.riot.transformer import parse_account_to_player

CACHE_KEY_PLAYER_STATS = "metascope:player_stats:{puuid}"


def _stats_cache_key(puuid: str) -> str:
    return CACHE_KEY_PLAYER_STATS.format(puuid=puuid)


async def get_player_stats(
    db: AsyncSession,
    puuid: str,
) -> PlayerStatsResponse:
    """Get aggregated stats for a player from match history."""
    cache_key = _stats_cache_key(puuid)

    cached, is_hit = await cache.cache_get_or_set(
        cache_key,
        settings.cache_ttl_player,
        _compute_player_stats,
        db,
        puuid,
    )
    return cached


async def _compute_player_stats(db: AsyncSession, puuid: str) -> PlayerStatsResponse:
    """Compute player stats from DB — called on cache miss."""
    player = await get_player_by_puuid(db, puuid)
    if not player:
        raise PlayerNotFoundError(puuid=puuid)

    stmt = (
        select(MatchParticipant)
        .join(Match, MatchParticipant.match_id == Match.id)
        .options(selectinload(MatchParticipant.units))
        .where(MatchParticipant.puuid == puuid)
        .order_by(Match.game_datetime.desc())
    )
    result = await db.execute(stmt)
    participants = result.scalars().all()

    if not participants:
        return PlayerStatsResponse(
            puuid=puuid,
            game_name=player.game_name,
            tag_line=player.tag_line,
            region=player.region,
            total_matches=0,
            wins=0,
            top4s=0,
            win_rate=0.0,
            top4_rate=0.0,
            avg_placement=0.0,
            top_champions=[],
            top_augments=[],
            avg_level=0.0,
            avg_gold_left=0.0,
            avg_damage=0.0,
            patches_played=[],
        )

    total = len(participants)
    wins = sum(1 for p in participants if p.placement == 1)
    top4s = sum(1 for p in participants if p.placement <= 4)
    total_placement = sum(p.placement for p in participants)

    top_champions = _aggregate_top_champions(db, participants)
    top_augments = _aggregate_top_augments(db, participants)
    patches = list({p.match.patch for p in participants if p.match and p.match.patch})

    avg_level = sum(p.level for p in participants) / total
    avg_gold_left = sum(p.gold_left for p in participants) / total
    avg_damage = sum(p.total_damage_to_players for p in participants) / total

    return PlayerStatsResponse(
        puuid=puuid,
        game_name=player.game_name,
        tag_line=player.tag_line,
        region=player.region,
        total_matches=total,
        wins=wins,
        top4s=top4s,
        win_rate=round(wins / total, 4),
        top4_rate=round(top4s / total, 4),
        avg_placement=round(total_placement / total, 2),
        top_champions=top_champions,
        top_augments=top_augments,
        avg_level=round(avg_level, 2),
        avg_gold_left=round(avg_gold_left, 1),
        avg_damage=round(avg_damage, 1),
        patches_played=sorted(patches),
    )


async def _aggregate_top_champions(
    db: AsyncSession,
    participants: list[MatchParticipant],
) -> list[ChampionUseStat]:
    """Aggregate champion usage from participants."""
    champ_counts: dict[str, int] = defaultdict(int)
    champ_wins: dict[str, int] = defaultdict(int)

    for p in participants:
        for unit in p.units:
            champ_counts[unit.unit_id] += 1
            if p.placement == 1:
                champ_wins[unit.unit_id] += 1

    sorted_champs = sorted(champ_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    champ_ids = [c[0] for c in sorted_champs]
    champ_map: dict[str, Champion] = {}
    if champ_ids:
        result = await db.execute(
            select(Champion).where(Champion.unit_id.in_(champ_ids))
        )
        for c in result.scalars():
            champ_map[c.unit_id] = c

    return [
        ChampionUseStat(
            unit_id=uid,
            name=champ_map.get(uid, type("C", (), {"name": uid})()).name or uid,
            games=games,
            win_rate=round(champ_wins[uid] / games, 4) if games else 0.0,
        )
        for uid, games in sorted_champs
    ]


async def _aggregate_top_augments(
    db: AsyncSession,
    participants: list[MatchParticipant],
) -> list[AugmentUseStat]:
    """Aggregate augment usage from participants."""
    aug_counts: dict[str, int] = defaultdict(int)
    aug_wins: dict[str, int] = defaultdict(int)

    for p in participants:
        for aug_id in (p.augments or []):
            aug_counts[aug_id] += 1
            if p.placement == 1:
                aug_wins[aug_id] += 1

    sorted_augs = sorted(aug_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    aug_ids = [a[0] for a in sorted_augs]
    aug_map: dict[str, Augment] = {}
    if aug_ids:
        result = await db.execute(
            select(Augment).where(Augment.augment_id.in_(aug_ids))
        )
        for a in result.scalars():
            aug_map[a.augment_id] = a

    return [
        AugmentUseStat(
            augment_id=aid,
            name=aug_map.get(aid, type("A", (), {"name": aid})()).name or aid,
            games=games,
            win_rate=round(aug_wins[aid] / games, 4) if games else 0.0,
        )
        for aid, games in sorted_augs
    ]


async def invalidate_player_stats(puuid: str) -> None:
    """Invalidate player stats cache when new matches are collected."""
    await cache.cache_delete(_stats_cache_key(puuid))


async def lookup_player(
    db: AsyncSession,
    game_name: str,
    tag_line: str,
    riot_client: RiotClient,
    region: str = "vn2",
) -> Player:
    """Lookup player by Riot ID — fetch from API if not in DB or stale."""
    stmt = select(Player).where(
        Player.game_name == game_name,
        Player.tag_line == tag_line,
    )
    result = await db.execute(stmt)
    player = result.scalars().first()

    if player and _is_fresh(player):
        return player

    account = await riot_client.get_account_by_riot_id(game_name, tag_line)
    if not account:
        raise PlayerNotFoundError(game_name, tag_line)

    summoner = await riot_client.get_summoner_by_puuid(account["puuid"])
    player_data = parse_account_to_player(account, summoner or None)

    if player:
        for key, value in player_data.items():
            setattr(player, key, value)
        player.last_fetched_at = datetime.now(UTC)
    else:
        existing = await db.execute(select(Player).where(Player.puuid == player_data["puuid"]))
        player = existing.scalars().first()
        if player:
            for key, value in player_data.items():
                setattr(player, key, value)
            player.last_fetched_at = datetime.now(UTC)
        else:
            player = Player(
                **player_data,
                region=region,
                last_fetched_at=datetime.now(UTC),
            )
            db.add(player)
            return player

    return player


async def get_player_by_puuid(
    db: AsyncSession,
    puuid: str,
) -> Player | None:
    """Get player from DB by PUUID."""
    stmt = select(Player).where(Player.puuid == puuid)
    result = await db.execute(stmt)
    return result.scalars().first()


def _is_fresh(player: Player, max_age_seconds: int = 1800) -> bool:
    """Check if player data is recent enough (default 30 min)."""
    if not player.last_fetched_at:
        return False
    age = (datetime.now(UTC) - player.last_fetched_at.replace(tzinfo=UTC)).total_seconds()
    return age < max_age_seconds
