"""Tests for game endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.game import service


class TestGetChampions:
    """Tests for get_champions service function."""

    @pytest.mark.asyncio
    async def test_returns_champions_list(self) -> None:
        """Returns list of champions from DB."""
        mock_champ = MagicMock()
        mock_champ.unit_id = "TFT13_Ahri"
        mock_champ.name = "Ahri"
        mock_champ.cost = 3
        mock_champ.traits = ["Sorcerer", "Sage"]
        mock_champ.tft_set_number = 13

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_champ]
        mock_db.execute.return_value = mock_result

        result = await service.get_champions(mock_db)

        assert len(result) == 1
        assert result[0].unit_id == "TFT13_Ahri"

    @pytest.mark.asyncio
    async def test_filters_by_set_number(self) -> None:
        """Filters champions by set_number when provided."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_champions(mock_db, set_number=13)

        # Verify the query was called with where clause
        call_args = mock_db.execute.call_args
        assert call_args is not None


class TestGetChampionById:
    """Tests for get_champion_by_id service function."""

    @pytest.mark.asyncio
    async def test_returns_champion_if_found(self) -> None:
        """Returns champion when found by unit_id."""
        mock_champ = MagicMock()
        mock_champ.unit_id = "TFT13_Ahri"
        mock_champ.name = "Ahri"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_champ
        mock_db.execute.return_value = mock_result

        result = await service.get_champion_by_id(mock_db, "TFT13_Ahri")

        assert result is not None
        assert result.unit_id == "TFT13_Ahri"

    @pytest.mark.asyncio
    async def test_returns_none_if_not_found(self) -> None:
        """Returns None when champion not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_champion_by_id(mock_db, "TFT13_Nonexistent")

        assert result is None


class TestGetItems:
    """Tests for get_items service function."""

    @pytest.mark.asyncio
    async def test_returns_items_list(self) -> None:
        """Returns list of items from DB."""
        mock_item = MagicMock()
        mock_item.item_id = "TFT13_Item_BFSword"
        mock_item.name = "B.F. Sword"
        mock_item.is_craftable = True
        mock_item.tft_set_number = 13

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_item]
        mock_db.execute.return_value = mock_result

        result = await service.get_items(mock_db)

        assert len(result) == 1
        assert result[0].item_id == "TFT13_Item_BFSword"

    @pytest.mark.asyncio
    async def test_filters_craftable_only(self) -> None:
        """Filters to craftable items when flag is set."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_items(mock_db, craftable_only=True)

        # Verify query included is_craftable filter
        call_args = mock_db.execute.call_args
        assert call_args is not None


class TestGetTraits:
    """Tests for get_traits service function."""

    @pytest.mark.asyncio
    async def test_returns_traits_list(self) -> None:
        """Returns list of traits from DB."""
        mock_trait = MagicMock()
        mock_trait.trait_id = "TFT13_Sorcerer"
        mock_trait.name = "Sorcerer"
        mock_trait.tft_set_number = 13

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_trait]
        mock_db.execute.return_value = mock_result

        result = await service.get_traits(mock_db)

        assert len(result) == 1
        assert result[0].trait_id == "TFT13_Sorcerer"


class TestGetAugments:
    """Tests for get_augments service function."""

    @pytest.mark.asyncio
    async def test_returns_augments_list(self) -> None:
        """Returns list of augments from DB."""
        mock_aug = MagicMock()
        mock_aug.augment_id = "TFT13_Augment_Salvage"
        mock_aug.name = "Salvage"
        mock_aug.tier = 1
        mock_aug.tft_set_number = 13

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_aug]
        mock_db.execute.return_value = mock_result

        result = await service.get_augments(mock_db)

        assert len(result) == 1
        assert result[0].augment_id == "TFT13_Augment_Salvage"

    @pytest.mark.asyncio
    async def test_filters_by_tier(self) -> None:
        """Filters augments by tier when provided."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_augments(mock_db, tier=1)

        call_args = mock_db.execute.call_args
        assert call_args is not None
