"""Champion, Item, Augment, Trait models and stats tables."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, TimestampMixin


class Champion(CreatedAtMixin, Base):
    """TFT champion static data."""

    __tablename__ = "champions"

    unit_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cost: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    traits: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    ability_name: Mapped[str | None] = mapped_column(String(100))
    ability_desc: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict] = mapped_column(JSONB, server_default="'{}'")
    tft_set_number: Mapped[int] = mapped_column(nullable=False)
    patch_added: Mapped[str | None] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)

    __table_args__ = (
        Index("idx_champion_cost", "cost"),
    )


class Item(CreatedAtMixin, Base):
    """TFT item — components and completed."""

    __tablename__ = "items"

    item_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(200))
    is_component: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    is_craftable: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    is_embleme: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    is_spatula: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    composition: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    stats: Mapped[dict] = mapped_column(JSONB, server_default="'{}'")
    tft_set_number: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")


class Augment(CreatedAtMixin, Base):
    """TFT augment — silver, gold, prismatic."""

    __tablename__ = "augments"

    augment_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    icon: Mapped[str | None] = mapped_column(String(200))
    tft_set_number: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    __table_args__ = (
        Index("idx_augment_tier", "tier"),
    )


class Trait(CreatedAtMixin, Base):
    """TFT trait/synergy with breakpoints."""

    __tablename__ = "traits"

    trait_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tft_set_number: Mapped[int] = mapped_column(nullable=False)
    breakpoints: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'")
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    __table_args__ = (
        Index("idx_trait_set", "tft_set_number"),
    )


class ChampionStats(Base):
    """Champion performance stats per patch — TimescaleDB hypertable."""

    __tablename__ = "champion_stats"

    champion_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("champions.unit_id"), primary_key=True,
    )
    tft_set_number: Mapped[int] = mapped_column(primary_key=True)
    patch: Mapped[str] = mapped_column(String(10), primary_key=True)
    queue_type: Mapped[str] = mapped_column(String(20), server_default="'ranked'", primary_key=True)
    calculated_at: Mapped[datetime] = mapped_column(server_default="now()", primary_key=True)
    games_played: Mapped[int] = mapped_column(server_default="0")
    wins: Mapped[int] = mapped_column(server_default="0")
    top4s: Mapped[int] = mapped_column(server_default="0")
    total_placement: Mapped[Decimal] = mapped_column(server_default="0")
    win_rate: Mapped[Decimal | None] = mapped_column()
    top4_rate: Mapped[Decimal | None] = mapped_column()
    avg_placement: Mapped[Decimal | None] = mapped_column()
    pick_rate: Mapped[Decimal | None] = mapped_column()
    tier_score: Mapped[Decimal | None] = mapped_column()
    tier: Mapped[str | None] = mapped_column(String(1))

    __table_args__ = (
        Index("idx_cs_champion_patch", "champion_id", "patch", "queue_type"),
        Index("idx_cs_tier_score", "patch", "tier_score"),
    )


class ItemStats(Base):
    """Item performance stats per patch — TimescaleDB hypertable."""

    __tablename__ = "item_stats"

    item_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("items.item_id"), primary_key=True,
    )
    champion_id: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="'_overall'", primary_key=True,
    )
    tft_set_number: Mapped[int] = mapped_column(primary_key=True)
    patch: Mapped[str] = mapped_column(String(10), primary_key=True)
    queue_type: Mapped[str] = mapped_column(String(20), server_default="'ranked'", primary_key=True)
    calculated_at: Mapped[datetime] = mapped_column(server_default="now()", primary_key=True)
    games_played: Mapped[int] = mapped_column(server_default="0")
    win_rate: Mapped[Decimal | None] = mapped_column()
    top4_rate: Mapped[Decimal | None] = mapped_column()
    avg_placement: Mapped[Decimal | None] = mapped_column()


class AugmentStats(Base):
    """Augment performance stats — TimescaleDB hypertable."""

    __tablename__ = "augment_stats"

    augment_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("augments.augment_id"), primary_key=True,
    )
    tft_set_number: Mapped[int] = mapped_column(primary_key=True)
    patch: Mapped[str] = mapped_column(String(10), primary_key=True)
    queue_type: Mapped[str] = mapped_column(String(20), server_default="'ranked'", primary_key=True)
    stage: Mapped[str] = mapped_column(String(10), nullable=False, server_default="'_all'", primary_key=True)
    calculated_at: Mapped[datetime] = mapped_column(server_default="now()", primary_key=True)
    games_played: Mapped[int] = mapped_column(server_default="0")
    win_rate: Mapped[Decimal | None] = mapped_column()
    top4_rate: Mapped[Decimal | None] = mapped_column()
    avg_placement: Mapped[Decimal | None] = mapped_column()

    __table_args__ = (
        Index("idx_as_augment_patch", "augment_id", "patch", "queue_type"),
    )


class TraitStats(Base):
    """Trait performance stats — TimescaleDB hypertable."""

    __tablename__ = "trait_stats"

    trait_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("traits.trait_id"), primary_key=True,
    )
    active_tier: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    tft_set_number: Mapped[int] = mapped_column(primary_key=True)
    patch: Mapped[str] = mapped_column(String(10), primary_key=True)
    queue_type: Mapped[str] = mapped_column(String(20), server_default="'ranked'", primary_key=True)
    calculated_at: Mapped[datetime] = mapped_column(server_default="now()", primary_key=True)
    games_played: Mapped[int] = mapped_column(server_default="0")
    wins: Mapped[int] = mapped_column(server_default="0")
    top4s: Mapped[int] = mapped_column(server_default="0")
    total_placement: Mapped[Decimal] = mapped_column(server_default="0")
    win_rate: Mapped[Decimal | None] = mapped_column()
    top4_rate: Mapped[Decimal | None] = mapped_column()
    avg_placement: Mapped[Decimal | None] = mapped_column()

    __table_args__ = (
        Index("idx_ts_trait_patch", "trait_id", "patch", "queue_type"),
    )
