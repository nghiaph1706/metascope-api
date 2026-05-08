"""Match API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import MatchNotFoundError
from app.match import service
from app.match.schemas import (
    MatchDetailResponse,
    MatchHistoryResponse,
    MatchSummaryResponse,
    ParticipantResponse,
    UnitResponse,
)
from app.player.dependencies import get_riot_client
from app.ports.riot.client import RiotClient

router = APIRouter()


@router.get(
    "/player/{puuid}/matches",
    response_model=MatchHistoryResponse,
)
async def get_match_history(
    puuid: str,
    count: int = Query(default=20, ge=1, le=100),
    start: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    riot_client: RiotClient = Depends(get_riot_client),
) -> MatchHistoryResponse:
    """Get match history for a player."""
    matches = await service.get_match_history(db, puuid, riot_client, count, start)

    summaries = []
    for match in matches:
        player_participant = next(
            (p for p in match.participants if p.puuid == puuid), None
        )
        summaries.append(MatchSummaryResponse(
            match_id=match.match_id,
            patch=match.patch,
            game_datetime=match.game_datetime,
            game_length=match.game_length,
            placement=player_participant.placement if player_participant else 0,
            level=player_participant.level if player_participant else 0,
            augments=player_participant.augments if player_participant else [],
            tft_set_number=match.tft_set_number,
        ))

    return MatchHistoryResponse(data=summaries, total=len(summaries))


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetailResponse,
    responses={404: {"description": "Match not found"}},
)
async def get_match_detail(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    riot_client: RiotClient = Depends(get_riot_client),
) -> MatchDetailResponse:
    """Get full details of a single match."""
    match = await service.get_match_by_match_id(db, match_id)

    if not match:
        await service.fetch_and_store_match(db, match_id, riot_client)
        await db.flush()
        match = await service.get_match_by_match_id(db, match_id)

    if not match:
        raise MatchNotFoundError(match_id)

    participants = [
        ParticipantResponse(
            puuid=p.puuid,
            placement=p.placement,
            level=p.level,
            gold_left=p.gold_left,
            augments=p.augments or [],
            traits_active=p.traits_active or [],
            units=[
                UnitResponse(
                    unit_id=u.unit_id,
                    tier=u.tier,
                    rarity=u.rarity,
                    items=u.items or [],
                )
                for u in p.units
            ],
        )
        for p in match.participants
    ]

    return MatchDetailResponse(
        match_id=match.match_id,
        patch=match.patch,
        patch_major=match.patch_major,
        patch_minor=match.patch_minor,
        game_datetime=match.game_datetime,
        game_length=match.game_length,
        game_variation=match.game_variation,
        queue_id=match.queue_id,
        tft_set_number=match.tft_set_number,
        region=match.region,
        participants=participants,
    )
