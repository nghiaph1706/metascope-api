"""Match, MatchParticipant, ParticipantUnit models."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base, CreatedAtMixin, UUIDMixin


class Match(UUIDMixin, CreatedAtMixin, Base):
    """TFT match record."""

    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    patch: Mapped[str] = mapped_column(String(10), nullable=False)
    patch_major: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    patch_minor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    game_datetime: Mapped[datetime] = mapped_column(nullable=False)
    game_length: Mapped[int] = mapped_column(nullable=False)
    game_variation: Mapped[str | None] = mapped_column(String(50))
    queue_id: Mapped[int | None] = mapped_column()
    tft_set_number: Mapped[int | None] = mapped_column()
    tft_set_core_name: Mapped[str | None] = mapped_column(String(50))
    region: Mapped[str] = mapped_column(String(10), nullable=False)

    participants: Mapped[list["MatchParticipant"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_matches_patch", "patch"),
        Index("idx_matches_game_datetime", "game_datetime"),
        Index("idx_matches_patch_datetime", "patch", "game_datetime"),
    )


class MatchParticipant(UUIDMixin, CreatedAtMixin, Base):
    """Player participation in a match."""

    __tablename__ = "match_participants"

    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    puuid: Mapped[str] = mapped_column(String(78), nullable=False)
    placement: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gold_left: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    last_round: Mapped[int | None] = mapped_column(SmallInteger)
    players_eliminated: Mapped[int] = mapped_column(server_default="0")
    total_damage_to_players: Mapped[int] = mapped_column(server_default="0")
    augments: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    traits_active: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="'[]'")
    time_eliminated: Mapped[Decimal | None] = mapped_column()

    match: Mapped[Match] = relationship(back_populates="participants")
    units: Mapped[list["ParticipantUnit"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("placement BETWEEN 1 AND 8", name="ck_placement_range"),
        Index("idx_mp_match_id", "match_id"),
        Index("idx_mp_puuid", "puuid"),
        Index("idx_mp_placement", "placement"),
        Index("idx_mp_match_puuid", "match_id", "puuid"),
    )


class ParticipantUnit(UUIDMixin, CreatedAtMixin, Base):
    """Champion unit on a participant's board."""

    __tablename__ = "participant_units"

    participant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    rarity: Mapped[int | None] = mapped_column(SmallInteger)
    items: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")

    participant: Mapped[MatchParticipant] = relationship(back_populates="units")

    __table_args__ = (
        Index("idx_pu_participant_id", "participant_id"),
        Index("idx_pu_unit_id", "unit_id"),
    )
