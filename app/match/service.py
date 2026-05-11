"""Match business logic — fetch, store, query with caching and cursor pagination."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_client
from app.match.models import Match, MatchParticipant, ParticipantUnit
from app.ports.riot.client import RiotClient
from app.ports.riot.transformer import parse_match_response, parse_participant, parse_unit

log = get_logger(__name__)

CACHE_KEY_MATCH_IDS = "metascope:match_ids:{puuid}"


def _cache_key(puuid: str) -> str:
    return CACHE_KEY_MATCH_IDS.format(puuid=puuid)


async def get_match_history(
    db: AsyncSession,
    puuid: str,
    riot_client: RiotClient,
    count: int = 20,
    cursor: str | None = None,
) -> tuple[list[Match], str | None]:
    """Get match history for a player with cursor pagination and caching.

    Returns (matches, next_cursor). If next_cursor is None, no more results.
    """
    cache_key = _cache_key(puuid)
    cached_ids: list[str] | None = None

    # Try Redis cache first
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            cached_ids = json.loads(cached)
            log.info("match_history_cache_hit", puuid=puuid, count=len(cached_ids or []))
    except Exception as exc:
        log.warning("match_history_cache_error", error=str(exc))

    # Fetch match IDs from Riot if not cached
    if not cached_ids:
        match_ids = await riot_client.get_match_ids(puuid, count=100)
        cached_ids = match_ids[:100]

        # Store in Redis cache
        try:
            await redis_client.setex(
                cache_key,
                settings.cache_ttl_match_history,
                json.dumps(cached_ids),
            )
            log.info("match_history_cached", puuid=puuid, count=len(cached_ids))
        except Exception as exc:
            log.warning("match_history_cache_set_error", error=str(exc))

    # Filter IDs already in DB
    existing_ids = await _get_existing_match_ids(db, puuid)
    new_ids = [mid for mid in cached_ids if mid not in existing_ids]

    # Fetch and store new matches
    if new_ids:
        for match_id in new_ids[:20]:  # Cap at 20 new matches per request
            await fetch_and_store_match(db, match_id, riot_client)
        await db.flush()
        # Invalidate cache since we added new matches
        try:
            await redis_client.delete(cache_key)
        except Exception:
            pass

    # Query DB with cursor pagination
    matches = await _get_matches_cursor(db, puuid, count, cursor)
    next_cursor = _calc_next_cursor(matches, count)

    return matches, next_cursor


async def _get_existing_match_ids(db: AsyncSession, puuid: str) -> set[str]:
    """Get all match IDs already in DB for this player."""
    stmt = select(Match.match_id).join(MatchParticipant).where(MatchParticipant.puuid == puuid)
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def _get_matches_cursor(
    db: AsyncSession,
    puuid: str,
    count: int,
    cursor: str | None,
) -> list[Match]:
    """Query matches with cursor pagination using game_datetime."""
    query = select(Match).join(MatchParticipant).where(MatchParticipant.puuid == puuid)

    if cursor:
        cursor_dt = datetime.fromisoformat(cursor)
        query = query.where(Match.game_datetime < cursor_dt)

    query = query.order_by(Match.game_datetime.desc()).limit(count + 1)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


def _calc_next_cursor(matches: list[Match], count: int) -> str | None:
    """Calculate next cursor if more results exist."""
    if len(matches) <= count:
        return None
    return matches[count - 1].game_datetime.isoformat()


async def fetch_and_store_match(
    db: AsyncSession,
    match_id: str,
    riot_client: RiotClient,
) -> Match | None:
    """Fetch a single match from Riot and store in DB. Skip if already exists."""
    existing = await db.execute(select(Match).where(Match.match_id == match_id))
    if existing.scalars().first():
        return None

    raw = await riot_client.get_match_detail(match_id)
    match_data = parse_match_response(raw)
    if not match_data:
        return None

    match = Match(**match_data)

    for raw_participant in raw.get("info", {}).get("participants", []):
        participant_data = parse_participant(raw_participant)
        participant = MatchParticipant(**participant_data)

        for raw_unit in raw_participant.get("units", []):
            unit_data = parse_unit(raw_unit)
            unit = ParticipantUnit(**unit_data)
            participant.units.append(unit)

        match.participants.append(participant)

    db.add(match)
    log.info("match_stored", match_id=match_id)
    return match


async def get_match_by_match_id(
    db: AsyncSession,
    match_id: str,
) -> Match | None:
    """Get a single match by its Riot match ID."""
    stmt = select(Match).where(Match.match_id == match_id)
    result = await db.execute(stmt)
    return result.scalars().first()
