"""Game static data API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ChampionNotFoundError, ItemNotFoundError, TraitNotFoundError, AugmentNotFoundError
from app.game import service
from app.game.schemas import (
    AugmentBase,
    AugmentListResponse,
    ChampionBase,
    ChampionDetailResponse,
    ChampionListResponse,
    CraftRecipe,
    ItemBase,
    ItemCheatsheetResponse,
    ItemDetailResponse,
    ItemListResponse,
    TraitBase,
    TraitDetailResponse,
    TraitListResponse,
)

router = APIRouter(prefix="/game", tags=["Game"])


@router.get("/champions", response_model=ChampionListResponse)
async def list_champions(
    set_number: int | None = Query(default=None),
    is_active: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ChampionListResponse:
    """List all champions with optional set filter."""
    champions = await service.get_champions(db, set_number, is_active, limit)
    active_set = champions[0].tft_set_number if champions else None
    return ChampionListResponse(
        data=[ChampionBase.model_validate(c) for c in champions],
        total=len(champions),
        set_number=active_set,
    )


@router.get("/champions/{unit_id}", response_model=ChampionDetailResponse)
async def get_champion(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChampionDetailResponse:
    """Get detailed champion info by unit_id."""
    champion = await service.get_champion_by_id(db, unit_id)
    if not champion:
        raise ChampionNotFoundError(unit_id)
    return ChampionDetailResponse.model_validate(champion)


@router.get("/items", response_model=ItemListResponse)
async def list_items(
    set_number: int | None = Query(default=None),
    is_active: bool = Query(default=True),
    craftable_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> ItemListResponse:
    """List all items with optional filters."""
    items = await service.get_items(db, set_number, is_active, craftable_only, limit)
    active_set = items[0].tft_set_number if items else None
    return ItemListResponse(
        data=[ItemBase.model_validate(i) for i in items],
        total=len(items),
        set_number=active_set,
    )


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> ItemDetailResponse:
    """Get detailed item info by item_id."""
    item = await service.get_item_by_id(db, item_id)
    if not item:
        raise ItemNotFoundError(item_id)
    return ItemDetailResponse.model_validate(item)


@router.get("/traits", response_model=TraitListResponse)
async def list_traits(
    set_number: int | None = Query(default=None),
    is_active: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> TraitListResponse:
    """List all traits with optional set filter."""
    traits = await service.get_traits(db, set_number, is_active, limit)
    active_set = traits[0].tft_set_number if traits else None
    return TraitListResponse(
        data=[TraitBase.model_validate(t) for t in traits],
        total=len(traits),
        set_number=active_set,
    )


@router.get("/traits/{trait_id}", response_model=TraitDetailResponse)
async def get_trait(
    trait_id: str,
    db: AsyncSession = Depends(get_db),
) -> TraitDetailResponse:
    """Get detailed trait info by trait_id."""
    trait = await service.get_trait_by_id(db, trait_id)
    if not trait:
        raise TraitNotFoundError(trait_id)
    return TraitDetailResponse.model_validate(trait)


@router.get("/augments", response_model=AugmentListResponse)
async def list_augments(
    set_number: int | None = Query(default=None),
    is_active: bool = Query(default=True),
    tier: int | None = Query(default=None, ge=1, le=3),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> AugmentListResponse:
    """List all augments with optional filters."""
    augments = await service.get_augments(db, set_number, is_active, tier, limit)
    active_set = augments[0].tft_set_number if augments else None
    return AugmentListResponse(
        data=[AugmentBase.model_validate(a) for a in augments],
        total=len(augments),
        set_number=active_set,
    )


@router.get("/items/cheatsheet", response_model=ItemCheatsheetResponse)
async def get_item_cheatsheet(
    set_number: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ItemCheatsheetResponse:
    """Get craft table showing component A + component B = item.

    Returns all craftable items with their component recipes.
    """
    items = await service.get_items_cheatsheet(db, set_number)
    active_set = items[0].tft_set_number if items else None

    recipes = []
    for item in items:
        comps = item.composition or []
        if len(comps) >= 2:
            recipes.append(
                CraftRecipe(
                    component_1=comps[0],
                    component_2=comps[1] if len(comps) > 1 else None,
                    result_item_id=item.item_id,
                    result_name=item.name,
                    is_two_component=len(comps) == 2,
                )
            )

    return ItemCheatsheetResponse(
        recipes=recipes,
        total=len(recipes),
        set_number=active_set,
    )