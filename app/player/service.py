"""Player business logic."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import cache
from app.core.config import settings
from app.match.models import Match, MatchParticipant
from app.meta.models import Augment, Champion
from app.player.exceptions import PlayerNotFoundError
from app.player.models import Player
from app.player.schemas import (
    AugmentUseStat,
    ChampionUseStat,
    CompUseStat,
    PlayerAnalysisResponse,
    PlayerStatsResponse,
)
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
    return cached  # type: ignore[no-any-return]


async def _compute_player_stats(db: AsyncSession, puuid: str) -> PlayerStatsResponse:
    """Compute player stats from DB — called on cache miss."""
    player = await get_player_by_puuid(db, puuid)
    if not player:
        raise PlayerNotFoundError(game_name=puuid, tag_line="")

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
    participants: Sequence[MatchParticipant],
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
        result = await db.execute(select(Champion).where(Champion.unit_id.in_(champ_ids)))
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
    participants: Sequence[MatchParticipant],
) -> list[AugmentUseStat]:
    """Aggregate augment usage from participants."""
    aug_counts: dict[str, int] = defaultdict(int)
    aug_wins: dict[str, int] = defaultdict(int)

    for p in participants:
        for aug_id in p.augments or []:
            aug_counts[aug_id] += 1
            if p.placement == 1:
                aug_wins[aug_id] += 1

    sorted_augs = sorted(aug_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    aug_ids = [a[0] for a in sorted_augs]
    aug_map: dict[str, Augment] = {}
    if aug_ids:
        result = await db.execute(select(Augment).where(Augment.augment_id.in_(aug_ids)))
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


CACHE_KEY_PLAYER_ANALYSIS = "metascope:player_analysis:{puuid}"


def _analysis_cache_key(puuid: str) -> str:
    return CACHE_KEY_PLAYER_ANALYSIS.format(puuid=puuid)


async def get_player_analysis(
    db: AsyncSession,
    puuid: str,
) -> PlayerAnalysisResponse:
    """Get player analysis: comp patterns, strengths, weaknesses."""
    cache_key = _analysis_cache_key(puuid)

    cached, is_hit = await cache.cache_get_or_set(
        cache_key,
        settings.cache_ttl_analysis_summary,
        _compute_player_analysis,
        db,
        puuid,
    )
    return cached  # type: ignore[no-any-return]


async def _compute_player_analysis(
    db: AsyncSession,
    puuid: str,
) -> PlayerAnalysisResponse:
    """Compute player analysis from match history."""
    player = await get_player_by_puuid(db, puuid)
    if not player:
        raise PlayerNotFoundError(game_name=puuid, tag_line="")

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
        return PlayerAnalysisResponse(
            puuid=puuid,
            game_name=player.game_name,
            tag_line=player.tag_line,
            region=player.region,
            total_matches=0,
            most_played_comps=[],
            preferred_traits=[],
            strengths=[],
            weaknesses=[],
            avg_level=0.0,
            avg_gold_left=0.0,
            early_game_strength=0.0,
            late_game_strength=0.0,
            avg_damage=0.0,
            patches_played=[],
            recent_trend="stable",
            advice=[],
        )

    total = len(participants)

    # Most played comps — using trait fingerprinting
    most_played_comps = _aggregate_top_comps(db, participants)

    # Preferred traits
    preferred_traits = _aggregate_preferred_traits(participants)

    # Strengths & weaknesses
    strengths, weaknesses = _detect_strengths_weaknesses(
        participants, most_played_comps, preferred_traits
    )

    # Playstyle indicators
    avg_level = sum(p.level for p in participants) / total
    avg_gold_left = sum(p.gold_left for p in participants) / total
    avg_damage = sum(p.total_damage_to_players for p in participants) / total

    patches = list({p.match.patch for p in participants if p.match and p.match.patch})

    # Recent trend
    recent_trend = _compute_trend(participants)

    # Bilingual advice
    advice = _generate_advice(
        strengths, weaknesses, avg_level, avg_placement=sum(p.placement for p in participants) / total
    )

    return PlayerAnalysisResponse(
        puuid=puuid,
        game_name=player.game_name,
        tag_line=player.tag_line,
        region=player.region,
        total_matches=total,
        most_played_comps=most_played_comps,
        preferred_traits=preferred_traits,
        strengths=strengths,
        weaknesses=weaknesses,
        avg_level=round(avg_level, 2),
        avg_gold_left=round(avg_gold_left, 1),
        early_game_strength=0.0,  # requires round-level data
        late_game_strength=0.0,   # requires round-level data
        avg_damage=round(avg_damage, 1),
        patches_played=sorted(patches),
        recent_trend=recent_trend,
        advice=advice,
    )


def _aggregate_top_comps(
    db: AsyncSession,
    participants: Sequence[MatchParticipant],
) -> list[CompUseStat]:
    """Aggregate composition usage from participants using trait fingerprinting."""
    # Build trait fingerprint for each player
    comp_games: dict[str, dict[str, int]] = {}  # comp_id -> {wins, total, top4}

    for p in participants:
        traits = frozenset(
            t["name"]
            for t in (p.traits_active or [])
            if t.get("tier_current", 0) > 0
        )
        if not traits:
            # Fallback: use top 3 units by cost as proxy comp
            unit_costs = sorted(
                [(u.unit_id, u.rarity or 0) for u in p.units],
                key=lambda x: -x[1]
            )
            top_units = frozenset(u[0] for u in unit_costs[:3])
            comp_key = f"unit:{top_units}"
        else:
            comp_key = f"trait:{sorted(traits)}"

        if comp_key not in comp_games:
            comp_games[comp_key] = {"wins": 0, "total": 0, "top4": 0, "placement_sum": 0}

        comp_games[comp_key]["total"] += 1
        comp_games[comp_key]["placement_sum"] += p.placement
        if p.placement == 1:
            comp_games[comp_key]["wins"] += 1
        if p.placement <= 4:
            comp_games[comp_key]["top4"] += 1

    sorted_comps = sorted(comp_games.items(), key=lambda x: x[1]["total"], reverse=True)[:5]

    result = []
    for comp_key, stats in sorted_comps:
        games = stats["total"]
        result.append(CompUseStat(
            comp_id=comp_key,
            name=_comp_display_name(comp_key),
            games=games,
            win_rate=round(stats["wins"] / games, 4) if games else 0.0,
            top4_rate=round(stats["top4"] / games, 4) if games else 0.0,
            avg_placement=round(stats["placement_sum"] / games, 2) if games else 0.0,
        ))

    return result


def _comp_display_name(comp_key: str) -> str:
    """Generate a human-readable comp name from trait fingerprint."""
    if comp_key.startswith("trait:"):
        traits = comp_key[6:].strip("[]").replace("'", "").split(", ")
        return " / ".join(sorted(t[:12] for t in traits if t)) or "Unknown Comp"
    return comp_key.replace("unit:", "Units: ")


def _aggregate_preferred_traits(
    participants: Sequence[MatchParticipant],
) -> list[str]:
    """Aggregate most-used traits across player's matches."""
    trait_counts: dict[str, int] = {}
    for p in participants:
        for t in (p.traits_active or []):
            if t.get("tier_current", 0) > 0:
                name = t.get("name", "Unknown")
                trait_counts[name] = trait_counts.get(name, 0) + 1
    return [t for t, _ in sorted(trait_counts.items(), key=lambda x: -x[1])[:5]]


def _detect_strengths_weaknesses(
    participants: Sequence[MatchParticipant],
    comps: list[CompUseStat],
    traits: list[str],
) -> tuple[list[str], list[str]]:
    """Detect player strengths and weaknesses from match data."""
    total = len(participants)
    wins = sum(1 for p in participants if p.placement == 1)
    top4s = sum(1 for p in participants if p.placement <= 4)
    top2s = sum(1 for p in participants if p.placement <= 2)

    win_rate = wins / total if total > 0 else 0.0
    top4_rate = top4s / total if total > 0 else 0.0
    top2_rate = top2s / total if total > 0 else 0.0
    avg_level = sum(p.level for p in participants) / total
    avg_gold_left = sum(p.gold_left for p in participants) / total

    strengths: list[str] = []
    weaknesses: list[str] = []

    if win_rate >= 0.12:
        strengths.append("Tỷ lệ thắng cao / High win rate")
    if top4_rate >= 0.50:
        strengths.append("Top 4 rate ổn định / Consistent top 4 finish rate")
    if top2_rate >= 0.25:
        strengths.append("Sức mạnh late game tốt / Strong late-game performance")
    if avg_level >= 8.5:
        strengths.append("Level cao thường xuyên / Frequently reaches high levels")
    if avg_gold_left <= 10:
        strengths.append("Tiêu tiền hiệu quả / Efficient gold spending")

    if win_rate < 0.06:
        weaknesses.append("Tỷ lệ thắng thấp — thử chơi an toàn hơn / Low win rate — try playing more safely")
    if top4_rate < 0.35:
        weaknesses.append("Top 4 rate thấp — cải thiện early/mid game / Low top 4 rate — improve early/mid game")
    if avg_level < 7.5:
        weaknesses.append("Level thấp — đầu tư XP nhiều hơn / Low level — invest more in XP")
    if avg_gold_left > 30:
        weaknesses.append("Dư tiền — tiêu nhiều hơn để tăng силу / Excess gold — spend more to increase strength")

    # Comp-based analysis
    if comps:
        best_comp = comps[0]
        if best_comp.win_rate < 0.08:
            weaknesses.append(f"Comp '{best_comp.name}' hiệu quả thấp — thử thay đổi / Comp '{best_comp.name}' underperforming")

    return strengths, weaknesses


def _compute_trend(participants: Sequence[MatchParticipant]) -> str:
    """Compute recent performance trend from last 10 matches."""
    recent = list(participants)[:10]
    if len(recent) < 5:
        return "stable"

    mid = len(recent) // 2
    first_half = recent[mid:]
    second_half = recent[:mid]

    first_win_rate = sum(1 for p in first_half if p.placement == 1) / len(first_half)
    second_win_rate = sum(1 for p in second_half if p.placement == 1) / len(second_half)

    if second_win_rate - first_win_rate >= 0.10:
        return "improving"
    elif first_win_rate - second_win_rate >= 0.10:
        return "declining"
    return "stable"


def _generate_advice(
    strengths: list[str],
    weaknesses: list[str],
    avg_level: float,
    avg_placement: float,
) -> list[str]:
    """Generate bilingual improvement advice."""
    advice: list[str] = []

    if avg_level < 7.5:
        advice.append("Nên level lên 8 sớm hơn để outscale / Level to 8 earlier to outscale opponents")
    if avg_placement > 4.5:
        advice.append("Cải thiện board strength vào mid game / Improve board strength in mid game")
    if len(weaknesses) >= 2:
        advice.append("Tập trung vào một comp chính thay vì flex nhiều / Focus on one main comp instead of flexing")
    if avg_placement <= 3.5:
        advice.append("Bạn chơi tốt — thử aim for win streak / You're playing well — try aiming for a win streak")

    if not advice:
        advice.append("Tiếp tục học hỏi từ mỗi trận — data sẽ cải thiện / Keep learning from each match — data will improve")

    return advice


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
