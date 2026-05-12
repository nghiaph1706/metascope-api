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


class CompUseStat(CustomBaseModel):
    """Composition usage statistics."""

    comp_id: str
    name: str
    games: int
    win_rate: float
    top4_rate: float
    avg_placement: float


class PlayerAnalysisResponse(CustomBaseModel):
    """Player analysis: frequently used comps, strengths, weaknesses."""

    puuid: str
    game_name: str
    tag_line: str
    region: str
    total_matches: int
    # Comp patterns
    most_played_comps: list[CompUseStat]
    preferred_traits: list[str]
    # Strengths (win rate > 50% in key metrics)
    strengths: list[str]
    # Weaknesses (win rate < 45% in key areas)
    weaknesses: list[str]
    # Playstyle indicators
    avg_level: float
    avg_gold_left: float
    early_game_strength: float  # avg placement in rounds 1-10
    late_game_strength: float  # avg placement in rounds 15+
    avg_damage: float
    # Match quality
    patches_played: list[str]
    recent_trend: str  # "improving", "stable", "declining"
    advice: list[str]  # Bilingual VI/EN improvement suggestions


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
