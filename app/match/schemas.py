"""Match Pydantic schemas."""

from datetime import datetime
from typing import Any, ClassVar

from app.core.schemas import CustomBaseModel


class UnitResponse(CustomBaseModel):
    """Champion unit in a participant's board."""

    unit_id: str
    tier: int
    rarity: int | None = None
    items: ClassVar[list[str]] = []


class ParticipantResponse(CustomBaseModel):
    """Player participation in a match."""

    puuid: str
    placement: int
    level: int
    gold_left: int = 0
    augments: ClassVar[list[str]] = []
    traits_active: ClassVar[list[dict[str, Any]]] = []
    units: ClassVar[list[UnitResponse]] = []


class MatchSummaryResponse(CustomBaseModel):
    """Lightweight match info for history lists."""

    match_id: str
    patch: str
    game_datetime: datetime
    game_length: int
    placement: int
    level: int
    augments: ClassVar[list[str]] = []
    tft_set_number: int | None = None


class MatchDetailResponse(CustomBaseModel):
    """Full match details with all participants."""

    match_id: str
    patch: str
    patch_major: int
    patch_minor: int
    game_datetime: datetime
    game_length: int
    game_variation: str | None = None
    queue_id: int | None = None
    tft_set_number: int | None = None
    region: str
    participants: ClassVar[list[ParticipantResponse]] = []


class MatchHistoryResponse(CustomBaseModel):
    """Match history response with cursor pagination."""

    data: list[MatchSummaryResponse]
    next_cursor: str | None = None
    total: int | None = None
