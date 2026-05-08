"""Player Pydantic schemas."""

from datetime import datetime

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
    meta: dict | None = None
