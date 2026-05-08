"""Match Pydantic schemas."""

from datetime import datetime

from app.core.schemas import CustomBaseModel


class UnitResponse(CustomBaseModel):
    """Champion unit in a participant's board."""

    unit_id: str
    tier: int
    rarity: int | None = None
    items: list[str] = []


class ParticipantResponse(CustomBaseModel):
    """Player participation in a match."""

    puuid: str
    placement: int
    level: int
    gold_left: int = 0
    augments: list[str] = []
    traits_active: list[dict] = []
    units: list[UnitResponse] = []


class MatchSummaryResponse(CustomBaseModel):
    """Lightweight match info for history lists."""

    match_id: str
    patch: str
    game_datetime: datetime
    game_length: int
    placement: int
    level: int
    augments: list[str] = []
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
    participants: list[ParticipantResponse] = []


class MatchHistoryResponse(CustomBaseModel):
    """Match history response."""

    data: list[MatchSummaryResponse]
    total: int | None = None
