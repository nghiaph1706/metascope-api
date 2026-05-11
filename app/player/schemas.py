"""Player Pydantic schemas."""

from datetime import datetime
from typing import Any

from app.core.schemas import CustomBaseModel


class PlayerResponse(CustomBaseModel):
    """Player profile response."""

    puuid: str
    game_name: str
    tag_line: str
    region: str
    summoner_level: int | None = None
    profile_icon_id: int | None = None
    last_fetched_at: datetime | None = None


class PlayerLookupResponse(CustomBaseModel):
    """Response for player lookup — includes fresh indicator."""

    data: PlayerResponse
    meta: dict[str, Any] | None = None


class ChampionUseStat(CustomBaseModel):
    """Champion usage statistics."""

    unit_id: str
    name: str
    games: int
    win_rate: float


class AugmentUseStat(CustomBaseModel):
    """Augment usage statistics."""

    augment_id: str
    name: str
    games: int
    win_rate: float


class PlayerStatsResponse(CustomBaseModel):
    """Aggregated player statistics."""

    puuid: str
    game_name: str
    tag_line: str
    region: str
    total_matches: int
    wins: int
    top4s: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    top_champions: list[ChampionUseStat]
    top_augments: list[AugmentUseStat]
    avg_level: float
    avg_gold_left: float
    avg_damage: float
    patches_played: list[str]
