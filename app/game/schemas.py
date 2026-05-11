"""Game static data Pydantic schemas."""

from typing import Any

from app.core.schemas import CustomBaseModel


class ChampionBase(CustomBaseModel):
    """Base champion fields."""

    unit_id: str
    name: str
    cost: int
    traits: list[str] = []
    ability_name: str | None = None
    ability_desc: str | None = None


class ChampionListResponse(CustomBaseModel):
    """Response for champion list endpoint."""

    data: list[ChampionBase]
    total: int
    set_number: int | None = None


class ChampionDetailResponse(ChampionBase):
    """Detailed champion info with stats."""

    stats: dict[str, Any] = {}
    tft_set_number: int
    patch_added: str | None = None
    is_active: bool = True


class ItemBase(CustomBaseModel):
    """Base item fields."""

    item_id: str
    name: str
    description: str | None = None
    icon: str | None = None


class ItemListResponse(CustomBaseModel):
    """Response for item list endpoint."""

    data: list[ItemBase]
    total: int
    set_number: int | None = None


class ItemDetailResponse(ItemBase):
    """Detailed item info with composition and stats."""

    is_component: bool = False
    is_craftable: bool = False
    is_embleme: bool = False
    is_spatula: bool = False
    composition: list[str] = []
    stats: dict[str, Any] = {}
    tft_set_number: int | None = None
    is_active: bool = True


class CraftRecipe(CustomBaseModel):
    """A single craft recipe: component_a + component_b = result_item."""

    component_1: str
    component_2: str | None = None
    result_item_id: str
    result_name: str
    is_two_component: bool = True


class ItemCheatsheetResponse(CustomBaseModel):
    """Craft table response showing all item recipes."""

    recipes: list[CraftRecipe]
    total: int
    set_number: int | None = None


class TraitBase(CustomBaseModel):
    """Base trait fields."""

    trait_id: str
    name: str
    description: str | None = None


class TraitListResponse(CustomBaseModel):
    """Response for trait list endpoint."""

    data: list[TraitBase]
    total: int
    set_number: int | None = None


class TraitDetailResponse(TraitBase):
    """Detailed trait info with breakpoints."""

    tft_set_number: int
    breakpoints: list[dict[str, Any]] = []
    is_active: bool = True


class AugmentBase(CustomBaseModel):
    """Base augment fields."""

    augment_id: str
    name: str
    description: str | None = None
    tier: int = 1


class AugmentListResponse(CustomBaseModel):
    """Response for augment list endpoint."""

    data: list[AugmentBase]
    total: int
    set_number: int | None = None