"""Player API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.player import service
from app.player.dependencies import get_riot_client
from app.player.schemas import (
    PlayerAnalysisResponse,
    PlayerLookupResponse,
    PlayerResponse,
    PlayerStatsResponse,
)
from app.ports.riot.client import RiotClient

router = APIRouter()


@router.get(
    "/player/{region}/{game_name}/{tag_line}",
    response_model=PlayerLookupResponse,
    responses={404: {"description": "Player not found"}},
)
async def lookup_player(
    region: str,
    game_name: str,
    tag_line: str,
    db: AsyncSession = Depends(get_db),
    riot_client: RiotClient = Depends(get_riot_client),
) -> PlayerLookupResponse:
    """Lookup player by region and Riot ID (game_name#tag_line)."""
    player = await service.lookup_player(db, game_name, tag_line, riot_client, region=region)
    return PlayerLookupResponse(
        data=PlayerResponse.model_validate(player),
    )


@router.get(
    "/player/{puuid}/stats",
    response_model=PlayerStatsResponse,
    responses={404: {"description": "Player not found"}},
)
async def get_player_stats(
    puuid: str,
    db: AsyncSession = Depends(get_db),
) -> PlayerStatsResponse:
    """Get aggregated stats for a player from their match history."""
    return await service.get_player_stats(db, puuid)


@router.get(
    "/player/{puuid}/analysis",
    response_model=PlayerAnalysisResponse,
    responses={404: {"description": "Player not found"}},
)
async def get_player_analysis(
    puuid: str,
    db: AsyncSession = Depends(get_db),
) -> PlayerAnalysisResponse:
    """Analyze player's match history: frequently used comps, strengths, weaknesses."""
    return await service.get_player_analysis(db, puuid)
