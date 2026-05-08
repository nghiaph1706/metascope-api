"""Player SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, TimestampMixin, UUIDMixin


class Player(UUIDMixin, TimestampMixin, Base):
    """Riot player profile."""

    __tablename__ = "players"

    puuid: Mapped[str] = mapped_column(String(78), unique=True, nullable=False)
    game_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(10), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False, server_default="vn2")
    summoner_id: Mapped[str | None] = mapped_column(String(100))
    account_id: Mapped[str | None] = mapped_column(String(100))
    profile_icon_id: Mapped[int | None] = mapped_column()
    summoner_level: Mapped[int | None] = mapped_column()
    last_fetched_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("idx_players_game_name_tag", "game_name", "tag_line"),
    )
