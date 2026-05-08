"""Match business logic — fetch, store, query."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.match.models import Match, MatchParticipant, ParticipantUnit
from app.ports.riot.client import RiotClient
from app.ports.riot.transformer import parse_match_response, parse_participant, parse_unit

log = get_logger(__name__)


async def get_match_history(
    db: AsyncSession,
    puuid: str,
    riot_client: RiotClient,
    count: int = 20,
    start: int = 0,
) -> list[Match]:
    """Get match history for a player — fetch from Riot if not in DB."""
    match_ids = await riot_client.get_match_ids(puuid, count=count, start=start)
    if not match_ids:
        return []

    for match_id in match_ids:
        await fetch_and_store_match(db, match_id, riot_client)

    await db.flush()

    stmt = (
        select(Match)
        .join(MatchParticipant)
        .where(MatchParticipant.puuid == puuid)
        .order_by(Match.game_datetime.desc())
        .limit(count)
        .offset(start)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def fetch_and_store_match(
    db: AsyncSession,
    match_id: str,
    riot_client: RiotClient,
) -> Match | None:
    """Fetch a single match from Riot and store in DB. Skip if already exists."""
    existing = await db.execute(
        select(Match).where(Match.match_id == match_id)
    )
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
