"""Stats Pydantic schemas for Meta & Analytics endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.core.schemas import CustomBaseModel


class ChampionStatsResponse(CustomBaseModel):
    """Champion performance stats response."""

    champion_id: str
    name: str | None = None
    cost: int | None = None
    traits: list[str] = []
    games_played: int
    wins: int
    top4s: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    pick_rate: float
    tier_score: float
    tier: str
    patch: str
    tft_set_number: int


class ChampionStatsDetailResponse(ChampionStatsResponse):
    """Detailed champion stats with additional metrics."""

    stats: dict[str, Any] = {}
    ability_name: str | None = None
    ability_desc: str | None = None


class TierListResponse(CustomBaseModel):
    """Tier list response — champions ranked by tier."""

    data: list[ChampionStatsResponse]
    total: int
    patch: str
    tft_set_number: int


class ItemStatsResponse(CustomBaseModel):
    """Item performance stats response."""

    item_id: str
    name: str | None = None
    games_played: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    is_craftable: bool = False
    composition: list[str] = []
    stats: dict[str, Any] = {}
    tier: str | None = None
    patch: str
    tft_set_number: int | None = None


class AugmentStatsResponse(CustomBaseModel):
    """Augment performance stats response."""

    augment_id: str
    name: str | None = None
    tier: int
    description: str | None = None
    games_played: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    patch: str
    tft_set_number: int | None = None


class TraitStatsResponse(CustomBaseModel):
    """Trait performance stats response."""

    trait_id: str
    name: str | None = None
    description: str | None = None
    active_tier: int
    games_played: int
    wins: int
    top4s: int
    win_rate: float
    top4_rate: float
    avg_placement: float
    breakpoints: list[dict[str, Any]] = []
    patch: str
    tft_set_number: int


class PatchListResponse(CustomBaseModel):
    """List of patches with data available."""

    data: list[str]
    total: int


class PatchCompareResponse(CustomBaseModel):
    """Compare stats between two patches."""

    champion_changes: list[dict[str, Any]] = []
    item_changes: list[dict[str, Any]] = []
    augment_changes: list[dict[str, Any]] = []